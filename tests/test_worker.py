import pytest
from sqlalchemy import select

from opsatlas.db import Audit, Outbox, connect
from opsatlas.worker import export_audit, publish_pending


class Producer:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail

    def produce(self, topic, key, value, on_delivery):
        self.messages.append((topic, key, value))
        on_delivery("delivery failed" if self.fail else None, None)

    def flush(self, timeout):
        return 0


def test_outbox_delivered_only_after_ack(tmp_path):
    engine, sessions = connect(f"sqlite:///{tmp_path}/outbox.db")
    with sessions.begin() as session:
        session.add(Outbox(payload={"document_id": "doc", "revision": 1}))
    with pytest.raises(RuntimeError):
        publish_pending(sessions, Producer(fail=True))
    with sessions() as session:
        assert not session.scalar(select(Outbox)).published
    producer = Producer()
    publish_pending(sessions, producer)
    publish_pending(sessions, producer)
    assert len(producer.messages) == 1
    with sessions() as session:
        assert session.scalar(select(Outbox)).published
    engine.dispose()


def test_audit_export_uses_stable_id_and_failure_keeps_pending(tmp_path):
    engine, sessions = connect(f"sqlite:///{tmp_path}/audit.db")
    with sessions.begin() as session:
        session.add(Audit(tenant="demo", kind="test", payload={"safe": True}))

    class Collection:
        def __init__(self):
            self.fail = True
            self.documents = {}

        def update_one(self, query, update, upsert):
            if self.fail:
                raise RuntimeError("Mongo unavailable")
            self.documents.setdefault(query["_id"], update["$setOnInsert"])

    collection = Collection()
    with pytest.raises(RuntimeError):
        export_audit(sessions, collection)
    with sessions() as session:
        assert not session.scalar(select(Audit)).exported
    collection.fail = False
    export_audit(sessions, collection)
    export_audit(sessions, collection)
    assert len(collection.documents) == 1
    engine.dispose()

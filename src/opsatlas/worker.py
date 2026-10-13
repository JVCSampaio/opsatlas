import json
import logging
import time

from confluent_kafka import Consumer, Producer, TopicPartition
from pymongo import MongoClient
from sqlalchemy import select

from opsatlas.config import get_settings
from opsatlas.db import Audit, Outbox, connect
from opsatlas.retrieval import index_document


def publish_pending(sessions, producer):
    with sessions.begin() as session:
        for event in session.scalars(
            select(Outbox)
            .where(Outbox.published.is_(False))
            .with_for_update(skip_locked=True)
            .limit(50)
        ):
            errors = []
            producer.produce(
                "opsatlas.documents",
                key=event.payload["document_id"],
                value=json.dumps(event.payload),
                on_delivery=lambda error, msg, errors=errors: (
                    errors.append(error) if error else None
                ),
            )
            if producer.flush(10) or errors:
                raise RuntimeError("Kafka delivery failed; outbox remains pending")
            event.published = True


def export_audit(sessions, collection):
    with sessions.begin() as session:
        for event in session.scalars(select(Audit).where(Audit.exported.is_(False)).limit(100)):
            collection.update_one(
                {"_id": event.id},
                {
                    "$setOnInsert": {
                        "tenant": event.tenant,
                        "kind": event.kind,
                        "payload": event.payload,
                        "created_at": event.created_at,
                    }
                },
                upsert=True,
            )
            event.exported = True


def run():
    settings = get_settings()
    engine, sessions = connect(settings.database_url)
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap, "enable.idempotence": True})
    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap,
            "group.id": "opsatlas-indexer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe(["opsatlas.documents"])
    mongo = (
        MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
        if settings.mongo_url
        else None
    )
    collection = mongo.opsatlas.audit if mongo else None
    if collection is not None:
        collection.create_index([("tenant", 1), ("created_at", -1)])
    try:
        while True:
            message = None
            try:
                publish_pending(sessions, producer)
                message = consumer.poll(1)
                if message and not message.error():
                    payload = json.loads(message.value())
                    with sessions.begin() as session:
                        index_document(
                            session, payload["document_id"], payload["revision"], settings
                        )
                    consumer.commit(message=message, asynchronous=False)
                if collection is not None:
                    export_audit(sessions, collection)
            except Exception:
                logging.exception("worker_cycle_failed")
                # Do not skip a failed record: seek back before the next poll.
                if message and not message.error():
                    consumer.seek(
                        TopicPartition(message.topic(), message.partition(), message.offset())
                    )
                time.sleep(2)
    finally:
        consumer.close()
        if mongo:
            mongo.close()
        engine.dispose()


if __name__ == "__main__":
    run()

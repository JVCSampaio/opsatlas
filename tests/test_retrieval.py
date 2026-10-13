import pytest

from opsatlas.retrieval import lexical_vector, split_chunks, terms


def test_chunks_bounded_and_preserve_content():
    source = "alpha " * 500
    chunks = split_chunks(source)
    assert all(len(chunk) <= 900 for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == source.replace(" ", "")


def test_feature_hash_deterministic_and_normalized():
    vector = lexical_vector("Kafka Kafka partitions")
    assert vector == lexical_vector("Kafka Kafka partitions")
    assert sum(x * x for x in vector) == pytest.approx(1)


def test_portuguese_accents_normalized():
    assert terms("Validação da operação") == ["validacao", "da", "operacao"]

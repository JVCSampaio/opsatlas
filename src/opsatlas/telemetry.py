import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()
requests = Counter(
    "opsatlas_requests", "HTTP requests", ["method", "route", "status"], registry=registry
)
latency = Histogram("opsatlas_request_seconds", "HTTP duration", ["route"], registry=registry)
answers = Counter(
    "opsatlas_answers", "Answers by evidence outcome", ["mode", "abstained"], registry=registry
)
tokens = Counter("opsatlas_llm_tokens", "Provider reported tokens", ["kind"], registry=registry)


def configure(endpoint: str):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if endpoint:
        provider = TracerProvider(resource=Resource.create({"service.name": "opsatlas-api"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
    return trace.get_tracer("opsatlas")

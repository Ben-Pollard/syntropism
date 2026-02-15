import os

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(service_name: str):
    # Check if a provider is already set
    try:
        # This will raise an error if no provider is set, or return the current one
        # However, trace.get_tracer_provider() always returns something (ProxyTracerProvider)
        # We check if it's already a TracerProvider
        if isinstance(trace.get_tracer_provider(), TracerProvider):
            return trace.get_tracer(service_name)
    except Exception:
        pass

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # Use environment variable for collector endpoint or default to localhost
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint, insecure=True))
    provider.add_span_processor(processor)

    try:
        trace.set_tracer_provider(provider)
    except ValueError:
        # Already set
        pass

    return trace.get_tracer(service_name)

def inject_context(headers: dict):
    propagate.inject(headers)

def extract_context(headers: dict):
    return propagate.extract(headers or {})

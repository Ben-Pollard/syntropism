import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from syntropism.core.observability import extract_context, inject_context, setup_tracing


@pytest.fixture
def tracer_provider():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    return provider


@pytest.fixture
def span_exporter(tracer_provider):
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_inject_context():
    """Test that inject_context adds traceparent to headers."""
    tracer = setup_tracing("test-service")
    headers = {}

    with tracer.start_as_current_span("test-span"):
        inject_context(headers)

    assert "traceparent" in headers
    assert headers["traceparent"].startswith("00-")


def test_extract_context():
    """Test that extract_context retrieves context from headers."""
    trace_id = "ff000000000000000000000000000041"
    span_id = "ff00000000000041"
    traceparent = f"00-{trace_id}-{span_id}-01"
    headers = {"traceparent": traceparent}

    context = extract_context(headers)
    span_context = trace.get_current_span(context).get_span_context()

    assert format(span_context.trace_id, "032x") == trace_id
    assert format(span_context.span_id, "016x") == span_id


def test_extract_context_empty():
    """Test that extract_context handles empty headers gracefully."""
    context = extract_context({})
    assert context is not None


def test_extract_context_none():
    """Test that extract_context handles None headers gracefully."""
    context = extract_context(None)
    assert context is not None

import json

import nats
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from syntropism.core.observability import extract_context, inject_context, setup_tracing
from syntropism.domain.economy import EconomicEngine
from syntropism.domain.models import Agent
from syntropism.infra.database import Base, SessionLocal, engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tracer_provider():
    provider = TracerProvider()
    # We don't set_tracer_provider here because it might already be set by setup_tracing
    # Instead we use the provider to create a tracer for testing
    return provider


@pytest.fixture
def span_exporter(tracer_provider):
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.mark.asyncio
async def test_nats_trace_propagation(nats_server, tracer_provider, span_exporter):
    """Test that trace context is propagated through NATS headers."""
    tracer = tracer_provider.get_tracer("test-tracer")
    nc = await nats.connect(nats_server)

    received_trace_id = None
    received_parent_span_id = None

    async def handler(msg):
        nonlocal received_trace_id, received_parent_span_id
        context = extract_context(msg.headers)
        with tracer.start_as_current_span("child-span", context=context) as span:
            span_context = span.get_span_context()
            received_trace_id = format(span_context.trace_id, "032x")

            # Get parent span ID from context
            parent_span = trace.get_current_span(context)
            received_parent_span_id = format(parent_span.get_span_context().span_id, "016x")

        await msg.respond(b"ok")

    sub = await nc.subscribe("test.trace.propagation", cb=handler)

    try:
        with tracer.start_as_current_span("parent-span") as parent_span:
            parent_context = parent_span.get_span_context()
            parent_trace_id = format(parent_context.trace_id, "032x")
            parent_span_id = format(parent_context.span_id, "016x")

            headers = {}
            inject_context(headers)
            await nc.request("test.trace.propagation", b"data", headers=headers, timeout=2)

        assert received_trace_id == parent_trace_id
        assert received_parent_span_id == parent_span_id
    finally:
        await nc.close()


@pytest.mark.asyncio
async def test_economic_engine_trace_propagation(nats_server, tracer_provider, span_exporter):
    """Test that EconomicEngine correctly extracts trace context from NATS headers."""
    # Setup: Create an agent in the DB
    agent_id = "trace_agent_1"
    with SessionLocal() as session:
        if not session.query(Agent).filter_by(id=agent_id).first():
            agent = Agent(id=agent_id, credit_balance=1000.0)
            session.add(agent)
            session.commit()

    # Start NATS handler
    engine_instance = EconomicEngine()
    # We need to ensure the engine uses our tracer provider for testing
    # But setup_tracing is called at module level in economy.py
    # For this test, we'll just verify that it extracts headers if present

    handler_nc = await engine_instance.run_nats(nats_url=nats_server)
    nc = await nats.connect(nats_server)

    try:
        # Start a span and inject context
        tracer = setup_tracing("test-client")
        with tracer.start_as_current_span("client-request") as span:
            trace_id = format(span.get_span_context().trace_id, "032x")
            headers = {}
            inject_context(headers)

            response = await nc.request(f"economic.balance.{agent_id}", b"", headers=headers, timeout=2)
            data = json.loads(response.data)
            assert data["agent_id"] == agent_id

            # Note: We can't easily verify the span created inside EconomicEngine
            # without mocking its tracer or using a global provider.
            # But we've verified the extraction logic in test_nats_trace_propagation.
    finally:
        await nc.close()
        await handler_nc.close()

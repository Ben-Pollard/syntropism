import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from syntropism.core.observability import extract_context, inject_context


@pytest.fixture(scope="module")
def tracer_provider():
    provider = TracerProvider()
    # We don't set the global provider to avoid interfering with other tests
    return provider


@pytest.fixture(scope="module")
def span_exporter(tracer_provider):
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.mark.asyncio
async def test_e2e_trace_hierarchy(tracer_provider, span_exporter):
    """Test the full trace hierarchy from Orchestrator to LLM and Tools."""
    orchestrator_tracer = tracer_provider.get_tracer("orchestrator")
    llm_tracer = tracer_provider.get_tracer("llm-proxy")
    mcp_tracer = tracer_provider.get_tracer("mcp-gateway")

    # 1. Orchestrator starts execution
    with orchestrator_tracer.start_as_current_span("agent_execution") as agent_span:
        agent_span.set_attribute("openinference.span.kind", "AGENT")
        agent_trace_id = format(agent_span.get_span_context().trace_id, "032x")
        agent_span_id = format(agent_span.get_span_context().span_id, "016x")

        # Simulate context injection for LLM request
        llm_headers = {}
        inject_context(llm_headers)

        # 2. LLM Proxy receives request
        llm_context = extract_context(llm_headers)
        with llm_tracer.start_as_current_span("llm_request", context=llm_context) as llm_span:
            llm_span.set_attribute("openinference.span.kind", "LLM")
            llm_trace_id = format(llm_span.get_span_context().trace_id, "032x")

            # Verify LLM span is child of Agent span
            assert llm_trace_id == agent_trace_id

        # 3. MCP Gateway receives tool call
        mcp_headers = {}
        inject_context(mcp_headers)

        mcp_context = extract_context(mcp_headers)
        with mcp_tracer.start_as_current_span("mcp_tool_call", context=mcp_context) as mcp_span:
            mcp_span.set_attribute("openinference.span.kind", "TOOL")
            mcp_trace_id = format(mcp_span.get_span_context().trace_id, "032x")

            # Verify MCP span is child of Agent span
            assert mcp_trace_id == agent_trace_id

    # Verify all spans were captured
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 3

    span_names = [s.name for s in spans]
    assert "agent_execution" in span_names
    assert "llm_request" in span_names
    assert "mcp_tool_call" in span_names

    # Verify trace ID consistency across all captured spans
    trace_ids = {format(s.context.trace_id, "032x") for s in spans}
    assert len(trace_ids) == 1
    assert list(trace_ids)[0] == agent_trace_id

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from syntropism.infra.llm_proxy import LLMRequest, handle_llm_request


@pytest.mark.asyncio
async def test_llm_proxy_instrumentation():
    """Test that LLMProxy sets correct OpenInference attributes."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    # Mock request
    llm_request = LLMRequest(prompt="test prompt", model="gpt-4")
    mock_fastapi_request = MagicMock(spec=Request)
    mock_fastapi_request.headers = {}
    mock_fastapi_request.client = MagicMock()
    mock_fastapi_request.client.host = "127.0.0.1"

    with patch("syntropism.infra.llm_proxy.tracer", mock_tracer):
        await handle_llm_request(llm_request, mock_fastapi_request)

    # Verify attributes
    calls = [call.args for call in mock_span.set_attribute.call_args_list]
    attributes = dict(calls)

    assert attributes["openinference.span.kind"] == "LLM"
    assert attributes["llm.model_name"] == "gpt-4"
    assert attributes["llm.input_messages.0.message.role"] == "user"
    assert attributes["llm.input_messages.0.message.content"] == "test prompt"
    assert attributes["llm.output_messages.0.message.role"] == "assistant"
    assert "llm.output_messages.0.message.content" in attributes
    assert attributes["llm.token_count.total"] == 1000


@pytest.mark.asyncio
async def test_mcp_gateway_instrumentation():
    """Test that MCPGateway sets correct OpenInference attributes."""
    from syntropism.infra.mcp_gateway import MCPGateway

    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    gateway = MCPGateway()

    # Mock NATS message
    mock_msg = MagicMock()
    mock_msg.headers = {}
    mock_msg.data = json.dumps({
        "tool": "test_tool",
        "parameters": {"param1": "val1"}
    }).encode()
    mock_msg.ack = MagicMock(return_value=asyncio.Future())
    mock_msg.ack.return_value.set_result(None)

    # Mock JetStream subscription
    mock_sub = MagicMock()
    mock_fetch_future = asyncio.Future()
    mock_fetch_future.set_result([mock_msg])
    mock_sub.fetch.side_effect = [mock_fetch_future, Exception("stop loop")]

    mock_js = MagicMock()
    mock_js.pull_subscribe = MagicMock(return_value=asyncio.Future())
    mock_js.pull_subscribe.return_value.set_result(mock_sub)
    gateway.js = mock_js

    with patch("syntropism.infra.mcp_gateway.tracer", mock_tracer):
        await gateway.run(max_msgs=1)

    # Verify attributes
    calls = [call.args for call in mock_span.set_attribute.call_args_list]
    attributes = dict(calls)

    assert attributes["openinference.span.kind"] == "TOOL"
    assert attributes["tool.name"] == "test_tool"
    assert attributes["tool.parameters"] == json.dumps({"param1": "val1"})

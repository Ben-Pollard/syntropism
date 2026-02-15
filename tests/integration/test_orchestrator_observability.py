import asyncio
from unittest.mock import MagicMock, patch

import pytest

from syntropism.core.orchestrator import run_system_loop
from syntropism.domain.models import Agent, Bid, BidStatus, ResourceBundle, Workspace


@pytest.mark.asyncio
async def test_orchestrator_agent_span():
    """Test that run_system_loop creates an AGENT span for execution."""
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    # Mock session
    mock_session = MagicMock()

    # Mock agent and bid
    agent = Agent(id="test_agent_span")
    bundle = ResourceBundle(id="bundle_1", cpu_percent=10.0, memory_percent=10.0, attention_percent=10.0)
    bid = Bid(
        id="bid_1",
        from_agent_id=agent.id,
        status=BidStatus.WINNING,
        execution_id="exec_1",
        resource_bundle=bundle,
        resource_bundle_id=bundle.id,
        agent=agent
    )
    workspace = Workspace(agent_id=agent.id, filesystem_path="/tmp/test_workspace")

    mock_session.query.return_value.filter_by.return_value.all.return_value = [bid]
    mock_session.query.return_value.filter_by.return_value.first.side_effect = [workspace, None] # workspace, then execution

    # Mock NATS
    mock_nc = MagicMock()
    mock_nc.publish = MagicMock(return_value=asyncio.Future())
    mock_nc.publish.return_value.set_result(None)

    # Mock sandbox and other dependencies to avoid side effects
    with patch("syntropism.core.orchestrator.tracer", mock_tracer), \
         patch("syntropism.core.orchestrator.AllocationScheduler.run_allocation_cycle"), \
         patch("syntropism.core.orchestrator.MarketManager.update_prices"), \
         patch("syntropism.core.orchestrator.AttentionManager.get_pending_prompts", return_value=[]), \
         patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox_cls, \
         patch("os.path.exists", return_value=False), \
         patch("builtins.open", MagicMock()):

        mock_sandbox_cls.return_value.run_agent.return_value = (0, "test logs")
        await run_system_loop(mock_session, nc=mock_nc)

    # Verify span creation
    mock_tracer.start_as_current_span.assert_any_call("agent_execution")

    # Verify attributes
    calls = [call.args for call in mock_span.set_attribute.call_args_list]
    attributes = dict(calls)

    assert attributes["openinference.span.kind"] == "AGENT"
    assert attributes["agent.id"] == "test_agent_span"

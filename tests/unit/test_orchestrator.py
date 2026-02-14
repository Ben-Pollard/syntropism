import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.core.orchestrator import run_system_loop
from syntropism.domain.models import Agent, Bid, BidStatus, ResourceBundle, Workspace
from syntropism.infra.database import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_run_system_loop_calls_allocation_cycle(session):
    with patch("syntropism.core.scheduler.AllocationScheduler.run_allocation_cycle") as mock_allocation:
        mock_allocation.return_value = None  # Async mock needs to return something awaitable or be an AsyncMock

        # Use AsyncMock for async functions
        with patch("syntropism.core.scheduler.AllocationScheduler.run_allocation_cycle", new_callable=pytest.importorskip("unittest.mock").AsyncMock) as mock_allocation:
            await run_system_loop(session)
            mock_allocation.assert_called_once_with(session, nc=None)


@pytest.mark.asyncio
async def test_run_system_loop_executes_winning_bids(session, tmp_path):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    workspace_path = str(tmp_path / "workspace")
    os.makedirs(workspace_path)
    workspace = Workspace(id="ws-1", agent_id=agent.id, filesystem_path=workspace_path)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, duration_seconds=1.0)
    session.add_all([agent, workspace, bundle])
    session.flush()

    bid = Bid(from_agent_id=agent.id, resource_bundle_id=bundle.id, amount=10.0, status=BidStatus.WINNING, execution_id="exec-1")
    session.add(bid)
    session.commit()

    with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox_class:
        mock_sandbox = mock_sandbox_class.return_value
        mock_sandbox.run_agent.return_value = (0, "Success")

        await run_system_loop(session)

        mock_sandbox.run_agent.assert_called_once()
        assert bid.status == BidStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_system_loop_updates_bid_status(session, tmp_path):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    workspace_path = str(tmp_path / "workspace")
    os.makedirs(workspace_path)
    workspace = Workspace(id="ws-1", agent_id=agent.id, filesystem_path=workspace_path)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, duration_seconds=1.0)
    session.add_all([agent, workspace, bundle])
    session.flush()

    bid = Bid(from_agent_id=agent.id, resource_bundle_id=bundle.id, amount=10.0, status=BidStatus.WINNING, execution_id="exec-1")
    session.add(bid)
    session.commit()

    with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox_class:
        mock_sandbox = mock_sandbox_class.return_value
        mock_sandbox.run_agent.return_value = (0, "Success")

        await run_system_loop(session)

        session.refresh(bid)
        assert bid.status == BidStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_system_loop_updates_market_prices(session):
    with patch("syntropism.domain.market.MarketManager.update_prices") as mock_update:
        await run_system_loop(session)
        mock_update.assert_called_once_with(session)


@pytest.mark.asyncio
async def test_run_system_loop_processes_attention_prompts(session, monkeypatch):
    # Setup
    from syntropism.domain.models import Prompt
    agent = Agent(id="agent-1", credit_balance=100.0)
    session.add(agent)
    session.commit()

    prompt = Prompt(from_agent_id=agent.id, content="Test prompt", bid_amount=5.0)
    session.add(prompt)
    session.commit()

    # Mock input()
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")

    with patch("syntropism.domain.attention.AttentionManager.reward_prompt") as mock_reward:
        await run_system_loop(session)
        mock_reward.assert_called_once()


@pytest.mark.asyncio
async def test_env_json_created_for_execution(session, tmp_path):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    workspace_path = str(tmp_path / "workspace")
    os.makedirs(workspace_path)
    workspace = Workspace(id="ws-1", agent_id=agent.id, filesystem_path=workspace_path)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, duration_seconds=1.0, attention_percent=0.5)
    session.add_all([agent, workspace, bundle])
    session.flush()

    bid = Bid(from_agent_id=agent.id, resource_bundle_id=bundle.id, amount=10.0, status=BidStatus.WINNING, execution_id="exec-1")
    session.add(bid)
    session.commit()

    with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox_class:
        mock_sandbox = mock_sandbox_class.return_value
        mock_sandbox.run_agent.return_value = (0, "Success")

        await run_system_loop(session)

        env_json_path = os.path.join(workspace_path, "env.json")
        assert os.path.exists(env_json_path)
        import json
        with open(env_json_path) as f:
            env_data = json.load(f)
            assert env_data["agent_id"] == agent.id
            assert env_data["attention_share"] == 0.5

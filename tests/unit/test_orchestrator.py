import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.infra.database import Base
from syntropism.domain.models import Agent, AgentStatus, Bid, BidStatus, Execution, MarketState, ResourceBundle, Workspace

TEST_DATABASE_URL = "sqlite:///./test_orchestrator.db"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_orchestrator.db"):
        os.remove("./test_orchestrator.db")


@pytest.fixture
def sample_market_states(db_session):
    """Create sample market states for testing."""
    resources = [
        ("cpu", 10.0, 1.0),
        ("memory", 1024.0, 0.1),
        ("tokens", 1000000.0, 0.001),
        ("attention", 1.0, 10.0),
    ]
    for resource_type, supply, price in resources:
        ms = MarketState(
            resource_type=resource_type,
            available_supply=supply,
            current_market_price=price,
            current_utilization=0.0,
        )
        db_session.add(ms)
    db_session.commit()


@pytest.fixture
def sample_agent(db_session):
    """Create a sample agent with workspace."""
    workspace_path = "/tmp/test-workspace"
    os.makedirs(workspace_path, exist_ok=True)

    workspace = Workspace(agent_id="test-agent-1", filesystem_path=workspace_path)
    db_session.add(workspace)
    db_session.flush()

    agent = Agent(
        id="test-agent-1",
        credit_balance=100.0,
        status=AgentStatus.ALIVE,
        workspace_id=workspace.id,
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def sample_resource_bundle(db_session):
    """Create a sample resource bundle."""
    bundle = ResourceBundle(
        cpu_seconds=1.0,
        memory_mb=128.0,
        tokens=1000,
        attention_share=0.1,
    )
    db_session.add(bundle)
    db_session.commit()
    db_session.refresh(bundle)
    return bundle


def test_run_system_loop_calls_allocation_cycle(db_session, sample_market_states, sample_agent, sample_resource_bundle):
    """Test that run_system_loop calls allocation cycle."""
    from syntropism.core.orchestrator import run_system_loop

    # Create a bid that will be marked as WINNING by the allocation cycle
    bid = Bid(
        from_agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        amount=10.0,
        status=BidStatus.PENDING,
    )
    db_session.add(bid)
    db_session.commit()

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = []

                    run_system_loop(db_session)

                    # Verify allocation cycle was called
                    mock_allocate.run_allocation_cycle.assert_called_once_with(db_session)


def test_run_system_loop_executes_winning_bids(db_session, sample_market_states, sample_agent, sample_resource_bundle):
    """Test that run_system_loop executes winning bids."""
    from syntropism.core.orchestrator import run_system_loop

    # Create a bid that is already WINNING
    bid = Bid(
        from_agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    # Create execution record
    execution = Execution(
        agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.commit()

    bid.execution_id = execution.id
    db_session.commit()

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = []

                    run_system_loop(db_session)

                    # Verify sandbox was called
                    mock_sandbox_instance.run_agent.assert_called_once()
                    call_args = mock_sandbox_instance.run_agent.call_args
                    # Handle both positional and keyword arguments
                    if call_args[0]:
                        assert call_args[0][0] == sample_agent.id
                    else:
                        assert call_args[1]["agent_id"] == sample_agent.id


def test_run_system_loop_updates_bid_status(db_session, sample_market_states, sample_agent, sample_resource_bundle):
    """Test that run_system_loop updates bid status to COMPLETED."""
    from syntropism.core.orchestrator import run_system_loop

    # Create a bid that is WINNING
    bid = Bid(
        from_agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    execution = Execution(
        agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.commit()

    bid.execution_id = execution.id
    db_session.commit()

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = []

                    run_system_loop(db_session)

                    # Verify bid status updated to COMPLETED
                    db_session.refresh(bid)
                    assert bid.status == BidStatus.COMPLETED


def test_run_system_loop_updates_market_prices(db_session, sample_market_states, sample_agent):
    """Test that run_system_loop updates market prices."""
    from syntropism.core.orchestrator import run_system_loop

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = []

                    run_system_loop(db_session)

                    # Verify market update was called
                    mock_market.update_prices.assert_called_once_with(db_session)


def test_run_system_loop_processes_attention_prompts(db_session, sample_market_states, sample_agent):
    """Test that run_system_loop processes pending attention prompts."""
    from syntropism.domain.models import Prompt, PromptStatus
    from syntropism.core.orchestrator import run_system_loop

    # Create a pending prompt
    prompt = Prompt(
        from_agent_id=sample_agent.id,
        execution_id="test-execution-id",
        content={"text": "Test prompt"},
        bid_amount=5.0,
        status=PromptStatus.PENDING,
    )
    db_session.add(prompt)
    db_session.commit()

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = [prompt]

                    with patch("builtins.input", return_value="8 7 9"):
                        mock_attention.reward_prompt.return_value = MagicMock()

                        run_system_loop(db_session)

                        # Verify attention methods were called
                        mock_attention.get_pending_prompts.assert_called_once_with(db_session)
                        mock_attention.reward_prompt.assert_called_once()


def test_env_json_created_for_execution(db_session, sample_market_states, sample_agent, sample_resource_bundle):
    """Test that env.json is created for execution."""
    import json

    from syntropism.core.orchestrator import run_system_loop

    # Create a winning bid
    bid = Bid(
        from_agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    execution = Execution(
        agent_id=sample_agent.id,
        resource_bundle_id=sample_resource_bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.commit()

    bid.execution_id = execution.id
    db_session.commit()

    workspace_path = "/tmp/test-workspace"

    with patch("syntropism.core.orchestrator.AllocationScheduler") as mock_allocate:
        mock_allocate.run_allocation_cycle.return_value = None
        with patch("syntropism.core.orchestrator.ExecutionSandbox") as mock_sandbox:
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.run_agent.return_value = (0, "success")
            mock_sandbox.return_value = mock_sandbox_instance

            with patch("syntropism.core.orchestrator.MarketManager") as mock_market:
                mock_market.update_prices.return_value = None
                with patch("syntropism.core.orchestrator.AttentionManager") as mock_attention:
                    mock_attention.get_pending_prompts.return_value = []

                    run_system_loop(db_session)

                    # Verify env.json was created
                    env_json_path = os.path.join(workspace_path, "env.json")
                    assert os.path.exists(env_json_path)

                    with open(env_json_path) as f:
                        env_data = json.load(f)

                    assert env_data["agent_id"] == sample_agent.id
                    assert env_data["execution_id"] == execution.id

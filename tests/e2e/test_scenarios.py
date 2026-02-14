import os
import threading
import time

import pytest
import uvicorn

from syntropism.cli import bootstrap_genesis_execution, seed_genesis_agent, seed_market_state
from syntropism.core.orchestrator import run_system_loop
from syntropism.domain.models import Agent, AgentStatus, Bid, BidStatus
from syntropism.infra.database import Base, SessionLocal, engine


@pytest.fixture(scope="module")
def server_port():
    return 8000


@pytest.fixture(scope="module")
def db_path():
    return "test_e2e.db"


@pytest.fixture(scope="module")
def server(db_path, server_port):
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass

    os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{db_path}"

    from syntropism.api.service import app

    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=server_port, log_level="error")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(2)
    yield

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass


@pytest.fixture
def db_session(server, db_path):
    # Clear the database for each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    seed_market_state(session)
    yield session
    session.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_survival_loop(db_session, monkeypatch):
    # 1. Setup Genesis
    agent = seed_genesis_agent(db_session)
    assert agent.id == "genesis"

    # 2. Run loop 1 (Bootstrap + Execution)
    bootstrap_genesis_execution(db_session)

    # Mock input() for the prompt triggered by bootstrap
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")

    db_session.commit()
    await run_system_loop(db_session)

    # 3. Verify agent executed once
    db_session.commit()
    db_session.refresh(agent)
    from syntropism.domain.models import Execution
    executions = db_session.query(Execution).filter_by(agent_id=agent.id, status="COMPLETED").count()
    assert executions == 1

    # 4. Verify agent placed a new PENDING bid during execution
    new_bid = db_session.query(Bid).filter_by(from_agent_id=agent.id, status=BidStatus.PENDING).first()
    assert new_bid is not None

    # 5. Run loop 2 (Allocation + Execution of new bid)
    db_session.commit()
    await run_system_loop(db_session)
    db_session.commit()
    db_session.refresh(agent)
    executions = db_session.query(Execution).filter_by(agent_id=agent.id, status="COMPLETED").count()
    assert executions == 2


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_human_interaction(db_session, monkeypatch):
    # 1. Setup agent with attention allocation
    agent = seed_genesis_agent(db_session)

    # 2. Bootstrap with attention_percent=1.0
    from syntropism.domain.models import Bid, BidStatus, Execution, ResourceBundle
    bundle = ResourceBundle(
        cpu_percent=0.1,
        memory_percent=0.1,
        tokens_percent=0.1,
        attention_percent=1.0,
        duration_seconds=5.0
    )
    db_session.add(bundle)
    db_session.flush()

    bid = Bid(
        from_agent_id=agent.id,
        resource_bundle_id=bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    execution = Execution(
        agent_id=agent.id,
        resource_bundle_id=bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.flush()
    bid.execution_id = execution.id
    agent.credit_balance -= 10.0
    db_session.commit()

    # 3. Mock input() for human scores
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")

    # 4. Run loop
    initial_balance = agent.credit_balance
    await run_system_loop(db_session)

    # 5. Verify credits awarded
    db_session.refresh(agent)
    assert agent.credit_balance > initial_balance


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_spawning(db_session, monkeypatch):
    # 1. Setup Genesis
    agent = seed_genesis_agent(db_session)

    # 2. Bootstrap
    bootstrap_genesis_execution(db_session)

    # 3. Mock input() for human scores
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")

    # 4. Run loop
    await run_system_loop(db_session)

    # 5. Verify child agent created
    child = db_session.query(Agent).filter(Agent.id != "genesis").first()
    assert child is not None
    assert child.spawn_lineage == ["genesis"]

    # 6. Verify child has a workspace
    assert child.workspace_id is not None

    # 7. Run loop again to execute child
    # Child needs a bid to be executed
    from syntropism.domain.models import Bid, BidStatus, Execution, ResourceBundle
    bundle = ResourceBundle(
        cpu_percent=0.1,
        memory_percent=0.1,
        tokens_percent=0.1,
        duration_seconds=5.0
    )
    db_session.add(bundle)
    db_session.flush()

    bid = Bid(
        from_agent_id=child.id,
        resource_bundle_id=bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    execution = Execution(
        agent_id=child.id,
        resource_bundle_id=bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.flush()
    bid.execution_id = execution.id
    child.credit_balance -= 10.0
    db_session.commit()

    # Run loop
    await run_system_loop(db_session)

    # Verify child executed
    db_session.commit()
    db_session.refresh(child)
    executions = db_session.query(Execution).filter_by(agent_id=child.id, status="COMPLETED").count()
    assert executions == 1


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_bid_competition(db_session):
    # 1. Setup two agents
    from syntropism.core.genesis import _create_agent_with_workspace
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    a1 = _create_agent_with_workspace(db_session, 100.0, [], os.path.join(workspace_root, "a1"), "agent1")
    a2 = _create_agent_with_workspace(db_session, 100.0, [], os.path.join(workspace_root, "a2"), "agent2")
    db_session.commit()

    # 2. Place bids for same limited resource (e.g. Attention)
    from syntropism.core.scheduler import AllocationScheduler
    from syntropism.domain.models import Bid, BidStatus, ResourceBundle

    # A1 bids 10 for attention
    b1_bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, attention_percent=1.0, duration_seconds=5.0)
    db_session.add(b1_bundle)
    db_session.flush()
    AllocationScheduler.place_bid(db_session, a1.id, b1_bundle.id, 10.0)

    # A2 bids 20 for attention
    b2_bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, attention_percent=1.0, duration_seconds=5.0)
    db_session.add(b2_bundle)
    db_session.flush()
    AllocationScheduler.place_bid(db_session, a2.id, b2_bundle.id, 20.0)

    db_session.commit()

    # 3. Run allocation
    await AllocationScheduler.run_allocation_cycle(db_session)
    db_session.commit()

    # 4. Verify A2 wins, A1 outbid
    bid1 = db_session.query(Bid).filter_by(from_agent_id=a1.id).first()
    bid2 = db_session.query(Bid).filter_by(from_agent_id=a2.id).first()

    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_death(db_session):
    # 1. Setup agent with 1 credit
    from syntropism.core.genesis import _create_agent_with_workspace
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    agent = _create_agent_with_workspace(db_session, 1.0, [], os.path.join(workspace_root, "poor_agent"), "poor_agent")
    db_session.commit()

    # 2. Place bid for 1 credit
    from syntropism.core.scheduler import AllocationScheduler
    from syntropism.domain.models import BidStatus, Execution, ResourceBundle

    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, duration_seconds=5.0)
    db_session.add(bundle)
    db_session.flush()

    # Use place_bid to ensure it's recorded correctly
    bid = AllocationScheduler.place_bid(db_session, agent.id, bundle.id, 1.0)

    # Manually mark as WINNING and create execution for the loop to process it
    bid.status = BidStatus.WINNING
    execution = Execution(
        agent_id=agent.id,
        resource_bundle_id=bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.flush()
    bid.execution_id = execution.id

    # Spend the credit
    agent.credit_balance -= 1.0
    db_session.commit()

    # 3. Run loop (Execution spends the credit, then death check runs)
    await run_system_loop(db_session)

    # 4. Verify status is DEAD
    db_session.commit()
    db_session.refresh(agent)
    assert agent.credit_balance <= 0
    assert agent.status == AgentStatus.DEAD

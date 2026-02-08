import os
import threading
import time

import pytest
import uvicorn

from syntropism.cli import bootstrap_genesis_execution, seed_genesis_agent, seed_market_state
from syntropism.database import Base, SessionLocal, engine
from syntropism.models import AgentStatus, Bid, BidStatus
from syntropism.orchestrator import run_system_loop


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

    from syntropism.service import app

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

@pytest.mark.e2e
def test_survival_loop(db_session, monkeypatch):
    # 1. Setup Genesis
    agent = seed_genesis_agent(db_session)
    assert agent.id == "genesis"

    # 2. Run loop 1 (Bootstrap + Execution)
    bootstrap_genesis_execution(db_session)

    # Mock input() for the prompt triggered by bootstrap
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")

    db_session.commit()
    run_system_loop(db_session)

    # 3. Verify agent executed once
    db_session.commit()
    db_session.refresh(agent)
    from syntropism.models import Execution
    executions = db_session.query(Execution).filter_by(agent_id=agent.id, status="COMPLETED").count()
    assert executions == 1

    # 4. Verify agent placed a new PENDING bid during execution
    new_bid = db_session.query(Bid).filter_by(from_agent_id=agent.id, status=BidStatus.PENDING).first()
    assert new_bid is not None

    # 5. Run loop 2 (Allocation + Execution of new bid)
    db_session.commit()
    run_system_loop(db_session)
    db_session.commit()
    db_session.refresh(agent)
    executions = db_session.query(Execution).filter_by(agent_id=agent.id, status="COMPLETED").count()
    assert executions == 2

@pytest.mark.e2e
def test_human_interaction(db_session, monkeypatch):
    # 1. Setup agent with attention allocation
    agent = seed_genesis_agent(db_session)

    # 2. Bootstrap with attention_share=1.0
    from syntropism.models import Bid, BidStatus, Execution, ResourceBundle
    bundle = ResourceBundle(
        cpu_seconds=5.0,
        memory_mb=128.0,
        tokens=1000,
        attention_share=1.0,
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
    run_system_loop(db_session)

    # 5. Verify credits awarded
    db_session.refresh(agent)
    assert agent.credit_balance > initial_balance

@pytest.mark.e2e
def test_agent_spawning(db_session):
    # 1. Setup parent
    parent = seed_genesis_agent(db_session)

    # 2. Manually trigger spawn
    from syntropism.genesis import spawn_child_agent
    payload = {
        "main.py": "print('Child agent running!')",
    }
    child = spawn_child_agent(db_session, parent.id, initial_credits=100.0, payload=payload)

    # 3. Verify child in DB
    assert child.id.startswith("agent-") or len(child.id) == 36 # UUID
    assert child.spawn_lineage == [parent.id]

    # 4. Verify child has a workspace
    assert child.workspace is not None
    assert os.path.exists(child.workspace.filesystem_path)

    # 5. Run loop and verify child can execute (if it has a bid)
    # Create a bid for the child
    from syntropism.models import Bid, BidStatus, Execution, ResourceBundle
    bundle = ResourceBundle(cpu_seconds=5.0, memory_mb=128.0, tokens=1000)
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
    run_system_loop(db_session)

    # Verify child executed
    db_session.commit()
    db_session.refresh(child)
    executions = db_session.query(Execution).filter_by(agent_id=child.id, status="COMPLETED").count()
    assert executions == 1

@pytest.mark.e2e
def test_bid_competition(db_session):
    # 1. Setup two agents
    from syntropism.genesis import _create_agent_with_workspace
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    a1 = _create_agent_with_workspace(db_session, 100.0, [], os.path.join(workspace_root, "a1"), "agent1")
    a2 = _create_agent_with_workspace(db_session, 100.0, [], os.path.join(workspace_root, "a2"), "agent2")
    db_session.commit()

    # 2. Place bids for same limited resource (e.g. Attention)
    from syntropism.models import Bid, BidStatus, ResourceBundle
    from syntropism.scheduler import AllocationScheduler

    # A1 bids 10 for attention
    b1_bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000, attention_share=1.0)
    db_session.add(b1_bundle)
    db_session.flush()
    AllocationScheduler.place_bid(db_session, a1.id, b1_bundle.id, 10.0)

    # A2 bids 20 for attention
    b2_bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000, attention_share=1.0)
    db_session.add(b2_bundle)
    db_session.flush()
    AllocationScheduler.place_bid(db_session, a2.id, b2_bundle.id, 20.0)

    db_session.commit()

    # 3. Run allocation
    AllocationScheduler.run_allocation_cycle(db_session)
    db_session.commit()

    # 4. Verify A2 wins, A1 outbid
    bid1 = db_session.query(Bid).filter_by(from_agent_id=a1.id).first()
    bid2 = db_session.query(Bid).filter_by(from_agent_id=a2.id).first()

    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID

@pytest.mark.e2e
def test_agent_death(db_session):
    # 1. Setup agent with 1 credit
    from syntropism.genesis import _create_agent_with_workspace
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    agent = _create_agent_with_workspace(db_session, 1.0, [], os.path.join(workspace_root, "poor_agent"), "poor_agent")
    db_session.commit()

    # 2. Place bid for 1 credit
    from syntropism.models import BidStatus, Execution, ResourceBundle
    from syntropism.scheduler import AllocationScheduler

    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000)
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
    run_system_loop(db_session)

    # 4. Verify status is DEAD
    db_session.commit()
    db_session.refresh(agent)
    assert agent.credit_balance <= 0
    assert agent.status == AgentStatus.DEAD

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bp_agents.database import Base
from bp_agents.dependencies import get_db
from bp_agents.genesis import SPAWN_COST, create_genesis_agent, spawn_child_agent
from bp_agents.models import Agent
from bp_agents.service import app


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_genesis_agent(db_session):
    agent = create_genesis_agent(db_session)

    assert agent.id is not None
    assert agent.credit_balance == 1000.0
    assert agent.spawn_lineage == []
    assert agent.workspace_id is not None

    # Verify it's in the DB
    saved_agent = db_session.query(Agent).filter(Agent.id == agent.id).first()
    assert saved_agent is not None
    assert saved_agent.workspace is not None


def test_spawn_child_agent(db_session):
    parent = create_genesis_agent(db_session)
    child_credits = 100.0

    child = spawn_child_agent(db_session, parent.id, child_credits)

    assert child.id is not None
    assert child.credit_balance == child_credits
    assert child.spawn_lineage == [parent.id]
    assert child.workspace_id is not None
    assert child.workspace.agent_id == child.id

    # Test multi-generational lineage
    grandchild = spawn_child_agent(db_session, child.id, 50.0)
    assert grandchild.spawn_lineage == [child.id, parent.id]


def test_spawn_child_agent_deducts_credits(db_session):
    parent = create_genesis_agent(db_session)
    initial_parent_balance = parent.credit_balance
    child_credits = 100.0

    child = spawn_child_agent(db_session, parent.id, child_credits)

    # Refresh parent from DB
    db_session.refresh(parent)

    expected_parent_balance = initial_parent_balance - child_credits - SPAWN_COST
    assert parent.credit_balance == expected_parent_balance
    assert child.credit_balance == child_credits


def test_spawn_child_agent_insufficient_funds(db_session):
    parent = create_genesis_agent(db_session)
    # Set balance to just below what's needed (SPAWN_COST + 100.0)
    parent.credit_balance = SPAWN_COST + 50.0
    db_session.commit()

    with pytest.raises(ValueError, match="Insufficient funds"):
        spawn_child_agent(db_session, parent.id, 100.0)


def test_spawn_child_agent_unique_workspaces(db_session):
    parent = create_genesis_agent(db_session)
    child1 = spawn_child_agent(db_session, parent.id, 10.0)
    child2 = spawn_child_agent(db_session, parent.id, 10.0)

    assert child1.workspace.filesystem_path != child2.workspace.filesystem_path


def test_spawn_agent_api(db_session, client):
    parent = create_genesis_agent(db_session)

    response = client.post("/social/spawn", json={"parent_id": parent.id, "initial_credits": 50.0})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "child_id" in data
    assert "workspace_id" in data


def test_spawn_child_agent_with_payload(db_session):
    parent = create_genesis_agent(db_session)
    payload = {"main.py": "print('hello')"}

    child = spawn_child_agent(db_session, parent.id, 10.0, payload=payload)

    import os

    file_path = os.path.join(child.workspace.filesystem_path, "main.py")
    assert os.path.exists(file_path)
    with open(file_path) as f:
        assert f.read() == "print('hello')"

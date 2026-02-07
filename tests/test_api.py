import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bp_agents.database import Base
from bp_agents.dependencies import get_db
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


def test_get_balance(db_session, client):
    # Create a test agent
    agent = Agent(id="test_agent", credit_balance=100.0)
    db_session.add(agent)
    db_session.commit()

    response = client.get("/economic/balance/test_agent")
    assert response.status_code == 200
    assert response.json() == {"agent_id": "test_agent", "balance": 100.0}


def test_get_balance_not_found(client):
    response = client.get("/economic/balance/non_existent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_transfer_credits(db_session, client):
    # Create test agents
    agent1 = Agent(id="agent1", credit_balance=100.0)
    agent2 = Agent(id="agent2", credit_balance=50.0)
    db_session.add(agent1)
    db_session.add(agent2)
    db_session.commit()

    transfer_data = {
        "from_id": "agent1",
        "to_id": "agent2",
        "amount": 30.0,
        "memo": "Test transfer",
    }
    response = client.post("/economic/transfer", json=transfer_data)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "amount": 30.0}

    # Verify balances
    response1 = client.get("/economic/balance/agent1")
    assert response1.json()["balance"] == 70.0
    response2 = client.get("/economic/balance/agent2")
    assert response2.json()["balance"] == 80.0


def test_transfer_insufficient_funds(db_session, client):
    # Create test agents
    agent1 = Agent(id="agent1", credit_balance=10.0)
    agent2 = Agent(id="agent2", credit_balance=50.0)
    db_session.add(agent1)
    db_session.add(agent2)
    db_session.commit()

    transfer_data = {
        "from_id": "agent1",
        "to_id": "agent2",
        "amount": 30.0,
        "memo": "Test transfer",
    }
    response = client.post("/economic/transfer", json=transfer_data)
    assert response.status_code == 400
    assert "insufficient funds" in response.json()["detail"].lower()


def test_transfer_agent_not_found(client):
    transfer_data = {
        "from_id": "non_existent",
        "to_id": "agent2",
        "amount": 30.0,
        "memo": "Test transfer",
    }
    response = client.post("/economic/transfer", json=transfer_data)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()

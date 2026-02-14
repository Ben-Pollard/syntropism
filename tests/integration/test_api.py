import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from syntropism.api.dependencies import get_db
from syntropism.api.service import app
from syntropism.domain.models import Agent
from syntropism.infra.database import Base


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


def test_send_message(db_session, client):
    # Create test agents
    agent1 = Agent(id="agent1", credit_balance=100.0)
    agent2 = Agent(id="agent2", credit_balance=50.0)
    db_session.add(agent1)
    db_session.add(agent2)
    db_session.commit()

    message_data = {
        "from_id": "agent1",
        "to_id": "agent2",
        "content": "Hello agent2!",
    }
    response = client.post("/social/message", json=message_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message_id" in response.json()


def test_place_bid(db_session, client):
    from syntropism.domain.models import ResourceBundle

    # Create test agent and bundle
    agent = Agent(id="agent1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle1", cpu_seconds=1.0, memory_mb=512.0, tokens=1000)
    db_session.add(agent)
    db_session.add(bundle)
    db_session.commit()

    bid_data = {
        "agent_id": "agent1",
        "bundle_id": "bundle1",
        "amount": 50.0,
    }
    response = client.post("/market/bid", json=bid_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "bid_id" in response.json()


def test_place_bid_with_requirements(db_session, client):
    # Create test agent
    agent = Agent(id="agent1", credit_balance=100.0)
    db_session.add(agent)
    db_session.commit()

    bid_data = {
        "agent_id": "agent1",
        "amount": 50.0,
        "cpu_seconds": 2.0,
        "memory_mb": 1024.0,
        "tokens": 5000,
        "attention_share": 0.5,
    }
    response = client.post("/market/bid", json=bid_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "bid_id" in response.json()

    # Verify ResourceBundle was created
    from syntropism.domain.models import Bid

    bid = db_session.query(Bid).filter(Bid.id == response.json()["bid_id"]).first()
    assert bid is not None
    assert bid.resource_bundle.cpu_seconds == 2.0
    assert bid.resource_bundle.memory_mb == 1024.0
    assert bid.resource_bundle.tokens == 5000
    assert bid.resource_bundle.attention_share == 0.5


def test_place_bid_invalid_request(client):
    """Test that missing bundle_id and resources returns 422 validation error."""
    bid_data = {
        "agent_id": "agent1",
        "amount": 50.0,
    }
    response = client.post("/market/bid", json=bid_data)
    # Pydantic validation returns 422 for invalid data
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "bundle_id" in str(detail) or "resource" in str(detail).lower()


def test_submit_prompt_validation(db_session, client):
    from syntropism.domain.models import Execution, ResourceBundle

    # Create test agent, bundle, and execution
    agent = Agent(id="agent1", credit_balance=100.0)
    bundle_no_attention = ResourceBundle(
        id="bundle1", cpu_seconds=1.0, memory_mb=512.0, tokens=1000, attention_share=0.0
    )
    bundle_with_attention = ResourceBundle(
        id="bundle2", cpu_seconds=1.0, memory_mb=512.0, tokens=1000, attention_share=0.1
    )

    execution1 = Execution(id="exec1", agent_id="agent1", resource_bundle_id="bundle1", status="running")
    execution2 = Execution(id="exec2", agent_id="agent1", resource_bundle_id="bundle2", status="running")

    db_session.add_all([agent, bundle_no_attention, bundle_with_attention, execution1, execution2])
    db_session.commit()

    # Try to submit prompt for execution without attention
    prompt_data = {
        "agent_id": "agent1",
        "execution_id": "exec1",
        "content": {"question": "What is 2+2?"},
        "bid_amount": 10.0,
    }
    response = client.post("/human/prompt", json=prompt_data)
    assert response.status_code == 400
    assert "Agent does not have attention allocation" in response.json()["detail"]

    # Try to submit prompt for execution with attention
    prompt_data["execution_id"] = "exec2"
    response = client.post("/human/prompt", json=prompt_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_get_market_prices(db_session, client):
    from syntropism.domain.models import MarketState

    # Seed market states
    states = [
        MarketState(resource_type="cpu", current_market_price=0.1),
        MarketState(resource_type="memory", current_market_price=0.05),
        MarketState(resource_type="tokens", current_market_price=0.01),
        MarketState(resource_type="attention", current_market_price=10.0),
    ]
    db_session.add_all(states)
    db_session.commit()

    response = client.get("/market/prices")
    assert response.status_code == 200
    assert response.json() == {"cpu": 0.1, "memory": 0.05, "tokens": 0.01, "attention": 10.0}

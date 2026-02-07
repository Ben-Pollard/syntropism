import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bp_agents.attention import AttentionManager
from bp_agents.database import Base
from bp_agents.dependencies import get_db
from bp_agents.models import Agent, Execution, Prompt, PromptStatus, ResourceBundle, Response, Transaction
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


def test_submit_prompt(db_session):
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    prompt = AttentionManager.submit_prompt(
        db_session,
        agent_id="agent-1",
        execution_id="exec-1",
        content={"question": "What is 2+2?"},
        bid_amount=10.0,
    )
    db_session.commit()

    assert prompt.id is not None
    assert prompt.from_agent_id == "agent-1"
    assert prompt.execution_id == "exec-1"
    assert prompt.content == {"question": "What is 2+2?"}
    assert prompt.bid_amount == 10.0
    assert prompt.status == PromptStatus.PENDING

    # Verify deduction
    updated_agent = db_session.query(Agent).filter(Agent.id == "agent-1").first()
    assert updated_agent.credit_balance == 90.0


def test_get_pending_prompts_ordered_by_bid(db_session):
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    exec1 = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    exec2 = Execution(id="exec-2", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, exec1, exec2])
    db_session.commit()

    AttentionManager.submit_prompt(db_session, "agent-1", "exec-1", {"q": "low bid"}, 5.0)
    AttentionManager.submit_prompt(db_session, "agent-1", "exec-2", {"q": "high bid"}, 15.0)
    db_session.commit()

    pending = AttentionManager.get_pending_prompts(db_session)

    assert len(pending) == 2
    assert pending[0].bid_amount == 15.0
    assert pending[1].bid_amount == 5.0


def test_reward_api(db_session, client):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    prompt = AttentionManager.submit_prompt(
        db_session,
        agent_id="agent-1",
        execution_id="exec-1",
        content={"question": "What is 2+2?"},
        bid_amount=10.0,
    )
    db_session.commit()
    prompt_id = prompt.id

    # Execute
    reward_data = {
        "prompt_id": prompt_id,
        "interesting": 8.0,
        "useful": 7.0,
        "understandable": 9.0,
        "reason": "Good question",
    }
    response = client.post("/human/reward", json=reward_data)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # (8+7+9) * 50 = 24 * 50 = 1200
    assert data["credits_awarded"] == 1200.0

    # Verify database state
    updated_prompt = db_session.query(Prompt).filter(Prompt.id == prompt_id).first()
    assert updated_prompt.status == PromptStatus.RESPONDED

    updated_agent = db_session.query(Agent).filter(Agent.id == "agent-1").first()
    # Initial 100 - 10 (bid) + 1200 (reward) = 1290
    assert updated_agent.credit_balance == 1290.0

    resp_obj = db_session.query(Response).filter(Response.prompt_id == prompt_id).first()
    assert resp_obj is not None
    assert resp_obj.credits_awarded == 1200.0

    # Verify transaction
    tx = (
        db_session.query(Transaction)
        .filter(Transaction.to_entity_id == "agent-1", Transaction.from_entity_id == "human")
        .first()
    )
    assert tx is not None
    assert tx.amount == 1200.0


def test_submit_prompt_insufficient_funds(db_session):
    agent = Agent(id="agent-1", credit_balance=5.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    with pytest.raises(ValueError, match="Insufficient funds"):
        AttentionManager.submit_prompt(
            db_session,
            agent_id="agent-1",
            execution_id="exec-1",
            content={"q": "test"},
            bid_amount=10.0,
        )


def test_reward_prompt_invalid_scores(db_session):
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    prompt = AttentionManager.submit_prompt(db_session, "agent-1", "exec-1", {"q": "test"}, 10.0)
    db_session.commit()
    prompt_id = prompt.id

    with pytest.raises(ValueError, match="Scores must be between 0 and 10"):
        AttentionManager.reward_prompt(db_session, prompt_id, interesting=11.0, useful=5.0, understandable=5.0)

    with pytest.raises(ValueError, match="Scores must be between 0 and 10"):
        AttentionManager.reward_prompt(db_session, prompt_id, interesting=-1.0, useful=5.0, understandable=5.0)


def test_reward_prompt_already_responded(db_session):
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    prompt = AttentionManager.submit_prompt(db_session, "agent-1", "exec-1", {"q": "test"}, 10.0)
    db_session.commit()
    prompt_id = prompt.id

    AttentionManager.reward_prompt(db_session, prompt_id, 5.0, 5.0, 5.0)
    db_session.commit()

    with pytest.raises(ValueError, match="already responded"):
        AttentionManager.reward_prompt(db_session, prompt_id, 5.0, 5.0, 5.0)


def test_submit_prompt_api(db_session, client):
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(id="bundle-1", attention_share=0.1)
    execution = Execution(id="exec-1", agent_id="agent-1", resource_bundle_id="bundle-1")
    db_session.add_all([agent, bundle, execution])
    db_session.commit()

    prompt_data = {
        "agent_id": "agent-1",
        "execution_id": "exec-1",
        "content": {"question": "API test"},
        "bid_amount": 20.0,
    }
    response = client.post("/human/prompt", json=prompt_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["prompt_id"] is not None

    # Verify deduction
    updated_agent = db_session.query(Agent).filter(Agent.id == "agent-1").first()
    assert updated_agent.credit_balance == 80.0

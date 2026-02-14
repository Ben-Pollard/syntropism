import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.domain.models import (
    Agent,
    AgentStatus,
    Bid,
    BidStatus,
    Execution,
    MarketState,
    Message,
    Prompt,
    PromptStatus,
    ResourceBundle,
    Transaction,
    Workspace,
)
from syntropism.infra.database import Base

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_agent_with_workspace(db_session):
    workspace = Workspace(agent_id="agent-1", filesystem_path="/tmp/agent-1")
    db_session.add(workspace)
    db_session.flush()

    agent = Agent(id="agent-1", credit_balance=1000.0, workspace_id=workspace.id, status=AgentStatus.ALIVE)
    db_session.add(agent)
    db_session.commit()

    saved_agent = db_session.query(Agent).filter(Agent.id == "agent-1").first()
    assert saved_agent.workspace.filesystem_path == "/tmp/agent-1"
    assert saved_agent.status == AgentStatus.ALIVE


def test_create_execution_with_bundle(db_session):
    agent = Agent(id="agent-1")
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=500, attention_share=0.0)
    db_session.add_all([agent, bundle])
    db_session.flush()

    execution = Execution(
        agent_id="agent-1", resource_bundle_id=bundle.id, status="completed", exit_code=0, termination_reason="success"
    )
    db_session.add(execution)
    db_session.commit()

    saved_execution = db_session.query(Execution).first()
    assert saved_execution.resource_bundle.cpu_seconds == 1.0
    assert saved_execution.exit_code == 0


def test_create_prompt_linked_to_execution(db_session):
    agent = Agent(id="agent-1")
    execution = Execution(agent_id="agent-1", status="running")
    db_session.add_all([agent, execution])
    db_session.flush()

    prompt = Prompt(
        id="prompt-1",
        from_agent_id="agent-1",
        execution_id=execution.id,
        content={"text": "Hello?"},
        bid_amount=5.0,
        status=PromptStatus.PENDING,
    )
    db_session.add(prompt)
    db_session.commit()

    saved_prompt = db_session.query(Prompt).first()
    assert saved_prompt.execution.status == "running"
    assert saved_prompt.status == PromptStatus.PENDING


def test_create_bid_with_bundle(db_session):
    agent = Agent(id="agent-1")
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=500, attention_share=1.0)
    db_session.add_all([agent, bundle])
    db_session.flush()

    bid = Bid(id="bid-1", from_agent_id="agent-1", resource_bundle_id=bundle.id, amount=10.0, status=BidStatus.PENDING)
    db_session.add(bid)
    db_session.commit()

    saved_bid = db_session.query(Bid).first()
    assert saved_bid.resource_bundle.attention_share == 1.0
    assert saved_bid.status == BidStatus.PENDING


def test_create_market_state(db_session):
    market = MarketState(
        resource_type="tokens", available_supply=10000.0, current_utilization=0.5, current_market_price=0.1
    )
    db_session.add(market)
    db_session.commit()

    saved_market = db_session.query(MarketState).first()
    assert saved_market.resource_type == "tokens"


def test_create_transaction(db_session):
    tx = Transaction(from_entity_id="agent-1", to_entity_id="agent-2", amount=50.0, memo="test transfer")
    db_session.add(tx)
    db_session.commit()

    saved_tx = db_session.query(Transaction).first()
    assert saved_tx.amount == 50.0


def test_create_message(db_session):
    agent1 = Agent(id="agent-1")
    agent2 = Agent(id="agent-2")
    db_session.add_all([agent1, agent2])

    msg = Message(from_agent_id="agent-1", to_agent_id="agent-2", content="hello")
    db_session.add(msg)
    db_session.commit()

    saved_msg = db_session.query(Message).first()
    assert saved_msg.content == "hello"

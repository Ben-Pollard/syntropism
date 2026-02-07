import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bp_agents.database import Base
from bp_agents.economy import EconomicEngine
from bp_agents.models import Agent

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


def test_transfer_credits_success(db_session):
    # Setup
    agent1 = Agent(id="agent-1", credit_balance=100.0)
    agent2 = Agent(id="agent-2", credit_balance=50.0)
    db_session.add_all([agent1, agent2])
    db_session.commit()

    # Execute
    EconomicEngine.transfer_credits(db_session, "agent-1", "agent-2", 30.0, "test transfer")
    db_session.commit()

    # Verify
    assert EconomicEngine.get_balance(db_session, "agent-1") == 70.0
    assert EconomicEngine.get_balance(db_session, "agent-2") == 80.0

    history = EconomicEngine.get_history(db_session, "agent-1")
    assert len(history) == 1
    assert history[0].amount == 30.0
    assert history[0].from_entity_id == "agent-1"
    assert history[0].to_entity_id == "agent-2"


def test_transfer_credits_insufficient_funds(db_session):
    # Setup
    agent1 = Agent(id="agent-1", credit_balance=20.0)
    agent2 = Agent(id="agent-2", credit_balance=50.0)
    db_session.add_all([agent1, agent2])
    db_session.commit()

    # Execute & Verify
    with pytest.raises(ValueError, match="Insufficient funds"):
        EconomicEngine.transfer_credits(db_session, "agent-1", "agent-2", 30.0, "test transfer")

    # Verify balances unchanged
    assert EconomicEngine.get_balance(db_session, "agent-1") == 20.0
    assert EconomicEngine.get_balance(db_session, "agent-2") == 50.0
    assert len(EconomicEngine.get_history(db_session, "agent-1")) == 0


def test_transfer_credits_atomicity(db_session):
    # Setup
    agent1 = Agent(id="agent-1", credit_balance=100.0)
    # agent2 does not exist, which should cause an error during transfer
    db_session.add(agent1)
    db_session.commit()

    # Execute & Verify
    with pytest.raises(ValueError):
        # This should fail because agent-2 doesn't exist
        EconomicEngine.transfer_credits(db_session, "agent-1", "non-existent", 30.0, "test transfer")
        db_session.commit()

    # Verify agent1 balance unchanged (atomicity)
    db_session.rollback()  # Ensure session is clean
    assert EconomicEngine.get_balance(db_session, "agent-1") == 100.0
    assert len(EconomicEngine.get_history(db_session, "agent-1")) == 0

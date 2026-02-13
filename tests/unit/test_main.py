import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.infra.database import Base
from syntropism.domain.models import Agent, AgentStatus, MarketState

# We'll mock the database for testing
TEST_DATABASE_URL = "sqlite:///./test_main.db"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_main.db"):
        os.remove("./test_main.db")


def test_init_db_seeds_market_state(db_session):
    # This test will verify that our seeding logic works
    from syntropism.cli import seed_market_state

    seed_market_state(db_session)

    market_states = db_session.query(MarketState).all()
    assert len(market_states) == 4

    cpu = db_session.query(MarketState).filter_by(resource_type="cpu").first()
    assert cpu.available_supply == 10.0
    assert cpu.current_market_price == 1.0

    memory = db_session.query(MarketState).filter_by(resource_type="memory").first()
    assert memory.available_supply == 1024.0
    assert memory.current_market_price == 0.1

    tokens = db_session.query(MarketState).filter_by(resource_type="tokens").first()
    assert tokens.available_supply == 1000000.0
    assert tokens.current_market_price == 0.001

    attention = db_session.query(MarketState).filter_by(resource_type="attention").first()
    assert attention.available_supply == 1.0
    assert attention.current_market_price == 10.0


def test_init_db_seeds_genesis_agent(db_session):
    from syntropism.cli import seed_genesis_agent

    seed_genesis_agent(db_session)

    # Genesis agent is created with 1000 credits and ALIVE status
    # The ID is a UUID, so we check for any agent with these properties
    genesis_agent = db_session.query(Agent).filter_by(credit_balance=1000.0).first()
    assert genesis_agent is not None
    assert genesis_agent.status == AgentStatus.ALIVE

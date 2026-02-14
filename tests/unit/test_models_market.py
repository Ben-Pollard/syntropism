import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.domain.models import MarketState, ResourceBundle
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


def test_resource_bundle_capacity_fields(db_session):
    """
    Verify that ResourceBundle supports capacity percentages and duration.
    """
    bundle = ResourceBundle(
        cpu_percent=0.5, memory_percent=0.25, tokens_percent=0.1, attention_percent=1.0, duration_seconds=60.0
    )
    db_session.add(bundle)
    db_session.commit()

    saved_bundle = db_session.query(ResourceBundle).first()
    assert saved_bundle.cpu_percent == 0.5
    assert saved_bundle.memory_percent == 0.25
    assert saved_bundle.tokens_percent == 0.1
    assert saved_bundle.attention_percent == 1.0
    assert saved_bundle.duration_seconds == 60.0


def test_market_state_capacity_supply(db_session):
    """
    Verify that MarketState tracks supply as a capacity measure.
    """
    market = MarketState(
        resource_type="cpu",
        available_supply=1.0,  # 100% capacity
        current_utilization=0.4,
        current_market_price=10.0,
    )
    db_session.add(market)
    db_session.commit()

    saved_market = db_session.query(MarketState).first()
    assert saved_market.available_supply == 1.0
    assert saved_market.current_utilization == 0.4

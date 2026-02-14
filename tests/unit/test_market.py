import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.domain.market import MarketManager, ResourceType
from syntropism.domain.models import MarketState
from syntropism.infra.database import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_prices_stay_within_bounds(session):
    # Setup: Very high utilization but price already high
    state = MarketState(
        resource_type=ResourceType.TOKENS.value,
        available_supply=100.0,
        current_utilization=0.9,
        current_market_price=MarketManager.MAX_PRICE + 100.0,
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.TOKENS)
    assert updated_state.current_market_price == MarketManager.MAX_PRICE

    # Setup: Very low utilization but price already low
    state_low = MarketState(
        resource_type=ResourceType.ATTENTION.value,
        available_supply=100.0,
        current_utilization=0.1,
        current_market_price=MarketManager.MIN_PRICE - 0.005,
    )
    session.add(state_low)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state_low = MarketManager.get_market_state(session, ResourceType.ATTENTION)
    assert updated_state_low.current_market_price == MarketManager.MIN_PRICE


def test_get_market_state_returns_none_for_unknown(session):
    state = MarketManager.get_market_state(session, ResourceType.CPU)
    assert state is None

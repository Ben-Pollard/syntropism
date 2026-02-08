import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.database import Base
from syntropism.market import MarketManager, ResourceType
from syntropism.models import MarketState


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_price_increases_when_utilization_high(session):
    # Setup: Initial price 1.0, utilization 0.9 (> 0.8)
    state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=100.0, current_utilization=0.9, current_market_price=1.0
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()  # Manual commit since we removed it from update_prices

    updated_state = MarketManager.get_market_state(session, ResourceType.CPU)
    assert updated_state.current_market_price > 1.0


def test_price_decreases_when_utilization_low(session):
    # Setup: Initial price 1.0, utilization 0.1 (< 0.2)
    state = MarketState(
        resource_type=ResourceType.MEMORY.value,
        available_supply=100.0,
        current_utilization=0.1,
        current_market_price=1.0,
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.MEMORY)
    assert updated_state.current_market_price < 1.0


def test_prices_stay_within_bounds(session):
    # Setup: Very high utilization but price already high
    state = MarketState(
        resource_type=ResourceType.TOKENS.value,
        available_supply=100.0,
        current_utilization=0.9,
        current_market_price=MarketManager.MAX_PRICE,
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.TOKENS)
    assert updated_state.current_market_price <= MarketManager.MAX_PRICE

    # Setup: Very low utilization but price already low
    state_low = MarketState(
        resource_type=ResourceType.ATTENTION.value,
        available_supply=100.0,
        current_utilization=0.1,
        current_market_price=MarketManager.MIN_PRICE,
    )
    session.add(state_low)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state_low = MarketManager.get_market_state(session, ResourceType.ATTENTION)
    assert updated_state_low.current_market_price >= MarketManager.MIN_PRICE


def test_middle_utilization_no_change(session):
    # Setup: Utilization exactly at thresholds should probably not change or have defined behavior
    # If we use >= 0.8 for increase and <= 0.2 for decrease, then 0.8 increases and 0.2 decreases.
    # Let's test that 0.5 (middle) doesn't change price.
    state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=100.0, current_utilization=0.5, current_market_price=1.0
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.CPU)
    assert updated_state.current_market_price == 1.0


def test_get_market_state_returns_none_for_unknown(session):
    state = MarketManager.get_market_state(session, ResourceType.CPU)
    assert state is None


def test_price_increases_by_10_percent_for_high_utilization(session):
    """Verify that prices increase by exactly 10% when utilization > 80%."""
    initial_price = 1.0
    state = MarketState(
        resource_type=ResourceType.CPU.value,
        available_supply=100.0,
        current_utilization=0.9,  # > 80%
        current_market_price=initial_price,
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.CPU)
    expected_price = initial_price * 1.1  # 10% increase
    assert updated_state.current_market_price == expected_price


def test_price_decreases_by_5_percent_for_low_utilization(session):
    """Verify that prices decrease by exactly 5% when utilization < 20%."""
    initial_price = 1.0
    state = MarketState(
        resource_type=ResourceType.MEMORY.value,
        available_supply=100.0,
        current_utilization=0.1,  # < 20%
        current_market_price=initial_price,
    )
    session.add(state)
    session.commit()

    MarketManager.update_prices(session)
    session.commit()

    updated_state = MarketManager.get_market_state(session, ResourceType.MEMORY)
    expected_price = initial_price * 0.95  # 5% decrease
    assert updated_state.current_market_price == expected_price

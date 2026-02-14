import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.core.scheduler import AllocationScheduler
from syntropism.domain.market import ResourceType
from syntropism.domain.models import Agent, MarketState, ResourceBundle
from syntropism.infra.database import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed market state
    cpu_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=10.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add(cpu_state)
    session.commit()

    yield session
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_price_discovery_from_winning_bids(session):
    """
    Verify that market price is discovered based on winning bids.
    Formula: total_credits / total_capacity_seconds
    """
    agent1 = Agent(id="agent-1", credit_balance=1000.0)
    agent2 = Agent(id="agent-2", credit_balance=1000.0)

    # Bundle 1: 1.0 CPU for 10 seconds = 10 capacity-seconds
    bundle1 = ResourceBundle(cpu_percent=1.0, duration_seconds=10.0)
    # Bundle 2: 2.0 CPU for 5 seconds = 10 capacity-seconds
    bundle2 = ResourceBundle(cpu_percent=2.0, duration_seconds=5.0)

    session.add_all([agent1, agent2, bundle1, bundle2])
    session.commit()

    # Agent 1 bids 50 for bundle 1
    AllocationScheduler.place_bid(session, agent1.id, bundle1.id, 50.0)
    # Agent 2 bids 150 for bundle 2
    AllocationScheduler.place_bid(session, agent2.id, bundle2.id, 150.0)

    # Run allocation
    await AllocationScheduler.run_allocation_cycle(session)

    # Total credits = 50 + 150 = 200
    # Total capacity-seconds = 10 + 10 = 20
    # New price = 200 / 20 = 10.0
    cpu_state = session.query(MarketState).filter_by(resource_type=ResourceType.CPU.value).first()
    assert cpu_state.current_market_price == 10.0

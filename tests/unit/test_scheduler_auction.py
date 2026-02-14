import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.core.scheduler import AllocationScheduler
from syntropism.domain.market import ResourceType
from syntropism.domain.models import Agent, BidStatus, MarketState, ResourceBundle
from syntropism.infra.database import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed market state
    cpu_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=1.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add(cpu_state)
    session.commit()

    yield session
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_allocation_capacity_based(session):
    """
    Verify that allocation is based on capacity (cpu_percent) rather than duration.
    """
    agent1 = Agent(id="agent-1", credit_balance=100.0)
    agent2 = Agent(id="agent-2", credit_balance=100.0)

    # Bundle 1: 40% CPU
    bundle1 = ResourceBundle(cpu_percent=0.4, duration_seconds=10.0)
    # Bundle 2: 70% CPU
    bundle2 = ResourceBundle(cpu_percent=0.7, duration_seconds=10.0)

    session.add_all([agent1, agent2, bundle1, bundle2])
    session.commit()

    # Agent 2 bids more for bundle 2 (70%)
    AllocationScheduler.place_bid(session, agent2.id, bundle2.id, 50.0)
    # Agent 1 bids less for bundle 1 (40%)
    AllocationScheduler.place_bid(session, agent1.id, bundle1.id, 10.0)

    # Run allocation
    await AllocationScheduler.run_allocation_cycle(session)

    # Agent 2 should win because they bid more and 70% fits in 100%
    # Agent 1 should be OUTBID because 70% + 40% > 100%
    bid1 = AllocationScheduler.get_history(session, agent1.id)[0]
    bid2 = AllocationScheduler.get_history(session, agent2.id)[0]

    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


@pytest.mark.asyncio
async def test_allocation_rejects_if_capacity_exceeded(session):
    """
    Verify that a bid is rejected if it exceeds remaining capacity, even if it's the only bid.
    """
    agent = Agent(id="agent-1", credit_balance=100.0)
    # Request 110% CPU
    bundle = ResourceBundle(cpu_percent=1.1, duration_seconds=10.0)

    session.add_all([agent, bundle])
    session.commit()

    AllocationScheduler.place_bid(session, agent.id, bundle.id, 10.0)

    await AllocationScheduler.run_allocation_cycle(session)

    bid = AllocationScheduler.get_history(session, agent.id)[0]
    assert bid.status == BidStatus.OUTBID


@pytest.mark.asyncio
async def test_allocation_all_or_nothing(session):
    """
    Verify that a bundle is only allocated if ALL its resource requirements are met.
    """
    # Add memory state
    mem_state = MarketState(
        resource_type=ResourceType.MEMORY.value, available_supply=1.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add(mem_state)
    session.commit()

    agent = Agent(id="agent-1", credit_balance=100.0)
    # Request 50% CPU (available) but 150% Memory (not available)
    bundle = ResourceBundle(cpu_percent=0.5, memory_percent=1.5, duration_seconds=10.0)

    session.add_all([agent, bundle])
    session.commit()

    AllocationScheduler.place_bid(session, agent.id, bundle.id, 10.0)

    await AllocationScheduler.run_allocation_cycle(session)

    bid = AllocationScheduler.get_history(session, agent.id)[0]
    assert bid.status == BidStatus.OUTBID

    # Verify CPU utilization didn't increase (atomicity of bundle allocation)
    cpu_state = session.query(MarketState).filter_by(resource_type=ResourceType.CPU.value).first()
    assert cpu_state.current_utilization == 0.0

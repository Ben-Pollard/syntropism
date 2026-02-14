import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.core.scheduler import AllocationScheduler
from syntropism.domain.market import ResourceType
from syntropism.domain.models import Agent, Bid, BidStatus, Execution, MarketState, ResourceBundle
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


@pytest.mark.asyncio
async def test_place_bid_success(session):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1)
    session.add_all([agent, bundle])
    session.commit()

    # Action
    bid = await AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)

    # Assert
    assert bid is not None
    assert bid.from_agent_id == agent.id
    assert bid.resource_bundle_id == bundle.id
    assert bid.amount == 50.0
    assert bid.status == BidStatus.PENDING

    # Verify in DB
    db_bid = session.query(Bid).filter_by(id=bid.id).first()
    assert db_bid is not None


@pytest.mark.asyncio
async def test_place_bid_insufficient_credits(session):
    # Setup
    agent = Agent(id="agent-1", credit_balance=10.0)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1)
    session.add_all([agent, bundle])
    session.commit()

    # Action & Assert
    with pytest.raises(ValueError, match="Insufficient credits"):
        await AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)


@pytest.mark.asyncio
async def test_place_bid_bundle_not_found(session):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    session.add(agent)
    session.commit()

    # Action & Assert
    with pytest.raises(ValueError, match="Bundle not found"):
        await AllocationScheduler.place_bid(session, agent.id, "non-existent-bundle", 50.0)


@pytest.mark.asyncio
async def test_allocation_highest_bidder_wins(session):
    # Setup
    agent1 = Agent(id="agent-1", credit_balance=100.0)
    agent2 = Agent(id="agent-2", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=1.0, memory_percent=0.1, tokens_percent=0.1, duration_seconds=1.0)
    # Market supply is only 1.0, but both agents want 1.0
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=1.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add_all([agent1, agent2, bundle, market_state])
    session.commit()

    # Place bids
    await AllocationScheduler.place_bid(session, agent1.id, bundle.id, 50.0)
    await AllocationScheduler.place_bid(session, agent2.id, bundle.id, 75.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid1 = session.query(Bid).filter_by(from_agent_id=agent1.id).first()
    bid2 = session.query(Bid).filter_by(from_agent_id=agent2.id).first()

    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


@pytest.mark.asyncio
async def test_allocation_supply_exhaustion(session):
    # Setup: 2 bundles available in market, 3 agents bidding for different bundles
    # Create 3 bundles of same type (e.g. CPU)
    bundle1 = ResourceBundle(cpu_percent=1.0, memory_percent=0.0, tokens_percent=0.0, duration_seconds=1.0)
    bundle2 = ResourceBundle(cpu_percent=1.0, memory_percent=0.0, tokens_percent=0.0, duration_seconds=1.0)
    bundle3 = ResourceBundle(cpu_percent=1.0, memory_percent=0.0, tokens_percent=0.0, duration_seconds=1.0)

    # Market supply is only 2
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=2.0, current_utilization=0.0, current_market_price=1.0
    )

    agent1 = Agent(id="agent-1", credit_balance=100.0)
    agent2 = Agent(id="agent-2", credit_balance=100.0)
    agent3 = Agent(id="agent-3", credit_balance=100.0)

    session.add_all([bundle1, bundle2, bundle3, market_state, agent1, agent2, agent3])
    session.commit()

    # Bids: Agent 3 (100), Agent 2 (50), Agent 1 (10)
    await AllocationScheduler.place_bid(session, agent1.id, bundle1.id, 10.0)
    await AllocationScheduler.place_bid(session, agent2.id, bundle2.id, 50.0)
    await AllocationScheduler.place_bid(session, agent3.id, bundle3.id, 100.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid3 = session.query(Bid).filter_by(from_agent_id=agent3.id).first()
    bid2 = session.query(Bid).filter_by(from_agent_id=agent2.id).first()
    bid1 = session.query(Bid).filter_by(from_agent_id=agent1.id).first()

    assert bid3.status == BidStatus.WINNING
    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


@pytest.mark.asyncio
async def test_allocation_deducts_credits(session):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.0, duration_seconds=1.0)
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=1.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add_all([agent, bundle, market_state])
    session.commit()

    await AllocationScheduler.place_bid(session, agent.id, bundle.id, 40.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    session.refresh(agent)
    assert agent.credit_balance == 60.0


@pytest.mark.asyncio
async def test_allocation_creates_execution_record(session):
    # Setup
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.0, duration_seconds=1.0)
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=1.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add_all([agent, bundle, market_state])
    session.commit()

    await AllocationScheduler.place_bid(session, agent.id, bundle.id, 40.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid = session.query(Bid).filter_by(from_agent_id=agent.id).first()
    assert bid.status == BidStatus.WINNING
    assert bid.execution_id is not None

    execution = session.query(Execution).filter_by(id=bid.execution_id).first()
    assert execution is not None
    assert execution.agent_id == agent.id
    assert execution.resource_bundle_id == bundle.id
    assert execution.status == "PENDING"


@pytest.mark.asyncio
async def test_allocation_prevents_negative_balance(session):
    # Setup: Agent has 100 credits, places two bids of 75 each.
    # Only one should win.
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle1 = ResourceBundle(cpu_percent=1.0, memory_percent=0.1, tokens_percent=0.0, duration_seconds=1.0)
    bundle2 = ResourceBundle(cpu_percent=1.0, memory_percent=0.1, tokens_percent=0.0, duration_seconds=1.0)
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=10.0, current_utilization=0.0, current_market_price=1.0
    )
    session.add_all([agent, bundle1, bundle2, market_state])
    session.commit()

    await AllocationScheduler.place_bid(session, agent.id, bundle1.id, 75.0)
    await AllocationScheduler.place_bid(session, agent.id, bundle2.id, 75.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    session.refresh(agent)
    assert agent.credit_balance >= 0
    winning_bids = session.query(Bid).filter_by(from_agent_id=agent.id, status=BidStatus.WINNING).all()
    assert len(winning_bids) == 1


@pytest.mark.asyncio
async def test_allocation_updates_market_utilization(session):
    # Setup
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=10.0, current_utilization=0.0, current_market_price=1.0
    )
    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=2.0, memory_percent=0.1, tokens_percent=0.0, duration_seconds=1.0)
    session.add_all([market_state, agent, bundle])
    session.commit()

    await AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session)

    # Assert
    session.refresh(market_state)
    assert market_state.current_utilization == 2.0

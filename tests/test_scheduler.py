import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bp_agents.database import Base
from bp_agents.models import Agent, Bid, BidStatus, Execution, MarketState, ResourceBundle
from bp_agents.scheduler import AllocationScheduler


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_place_bid_success(session):
    # Setup
    agent = Agent(credit_balance=100.0)
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000)
    session.add_all([agent, bundle])
    session.commit()

    # Action
    bid = AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)

    # Assert
    assert bid is not None
    assert bid.from_agent_id == agent.id
    assert bid.resource_bundle_id == bundle.id
    assert bid.amount == 50.0
    assert bid.status == BidStatus.PENDING

    # Verify in DB
    db_bid = session.query(Bid).filter_by(id=bid.id).first()
    assert db_bid is not None


def test_place_bid_insufficient_credits(session):
    # Setup
    agent = Agent(credit_balance=10.0)
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000)
    session.add_all([agent, bundle])
    session.commit()

    # Action & Assert
    with pytest.raises(ValueError, match="Insufficient credits"):
        AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)


def test_place_bid_bundle_not_found(session):
    # Setup
    agent = Agent(credit_balance=100.0)
    session.add(agent)
    session.commit()

    # Action & Assert
    with pytest.raises(ValueError, match="Bundle not found"):
        AllocationScheduler.place_bid(session, agent.id, "non-existent-bundle", 50.0)


def test_allocation_highest_bidder_wins(session):
    # Setup
    agent1 = Agent(credit_balance=100.0)
    agent2 = Agent(credit_balance=100.0)
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=1000)
    session.add_all([agent1, agent2, bundle])
    session.commit()

    # Place bids
    AllocationScheduler.place_bid(session, agent1.id, bundle.id, 50.0)
    AllocationScheduler.place_bid(session, agent2.id, bundle.id, 75.0)

    # Action
    AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid1 = session.query(Bid).filter_by(from_agent_id=agent1.id).first()
    bid2 = session.query(Bid).filter_by(from_agent_id=agent2.id).first()

    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


def test_allocation_supply_exhaustion(session):
    # Setup: 2 bundles available in market, 3 agents bidding for different bundles
    # Wait, the requirement says "Allocate bundles until supply exhausted".
    # This implies we should check MarketState for supply.

    from bp_agents.market import ResourceType

    # Create 3 bundles of same type (e.g. CPU)
    bundle1 = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=0)
    bundle2 = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=0)
    bundle3 = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=0)

    # Market supply is only 2
    market_state = MarketState(
        resource_type=ResourceType.CPU.value, available_supply=2.0, current_utilization=0.0, current_market_price=1.0
    )

    agent1 = Agent(credit_balance=100.0)
    agent2 = Agent(credit_balance=100.0)
    agent3 = Agent(credit_balance=100.0)

    session.add_all([bundle1, bundle2, bundle3, market_state, agent1, agent2, agent3])
    session.commit()

    # Bids: Agent 3 (100), Agent 2 (50), Agent 1 (10)
    AllocationScheduler.place_bid(session, agent1.id, bundle1.id, 10.0)
    AllocationScheduler.place_bid(session, agent2.id, bundle2.id, 50.0)
    AllocationScheduler.place_bid(session, agent3.id, bundle3.id, 100.0)

    # Action
    AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid3 = session.query(Bid).filter_by(from_agent_id=agent3.id).first()
    bid2 = session.query(Bid).filter_by(from_agent_id=agent2.id).first()
    bid1 = session.query(Bid).filter_by(from_agent_id=agent1.id).first()

    assert bid3.status == BidStatus.WINNING
    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID


def test_allocation_deducts_credits(session):
    # Setup
    agent = Agent(credit_balance=100.0)
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=0)
    session.add_all([agent, bundle])
    session.commit()

    AllocationScheduler.place_bid(session, agent.id, bundle.id, 40.0)

    # Action
    AllocationScheduler.run_allocation_cycle(session)

    # Assert
    session.refresh(agent)
    assert agent.credit_balance == 60.0


def test_allocation_creates_execution_record(session):
    # Setup
    agent = Agent(credit_balance=100.0)
    bundle = ResourceBundle(cpu_seconds=1.0, memory_mb=128.0, tokens=0)
    session.add_all([agent, bundle])
    session.commit()

    AllocationScheduler.place_bid(session, agent.id, bundle.id, 40.0)

    # Action
    AllocationScheduler.run_allocation_cycle(session)

    # Assert
    bid = session.query(Bid).filter_by(from_agent_id=agent.id).first()
    assert bid.status == BidStatus.WINNING
    assert bid.execution_id is not None

    execution = session.query(Execution).filter_by(id=bid.execution_id).first()
    assert execution is not None
    assert execution.agent_id == agent.id
    assert execution.resource_bundle_id == bundle.id
    assert execution.status == "PENDING"

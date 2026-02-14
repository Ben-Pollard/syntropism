import json
from unittest.mock import AsyncMock

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
    yield session
    session.close()
    engine.dispose()

@pytest.mark.asyncio
async def test_scheduler_emits_events(session):
    """
    Verify that the scheduler emits events to NATS.
    """
    nc = AsyncMock()

    # Setup market
    ms = MarketState(
        resource_type=ResourceType.CPU.value,
        available_supply=1.0,
        current_utilization=0.0,
        current_market_price=1.0
    )
    session.add(ms)

    agent = Agent(credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=0.5, duration_seconds=10.0)
    session.add_all([agent, bundle])
    session.commit()

    AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)

    # Action
    await AllocationScheduler.run_allocation_cycle(session, nc=nc)

    # Assert events were published
    # 1. system.market.bid_processed
    # 2. system.market.price_discovered

    assert nc.publish.called
    subjects = [call.args[0] for call in nc.publish.call_args_list]
    assert "system.market.bid_processed" in subjects
    assert "system.market.price_discovered" in subjects

    # Verify content of bid_processed
    bid_call = [c for c in nc.publish.call_args_list if c.args[0] == "system.market.bid_processed"][0]
    event_data = json.loads(bid_call.args[1].decode())
    assert event_data["agent_id"] == agent.id
    assert event_data["status"] == "winning"

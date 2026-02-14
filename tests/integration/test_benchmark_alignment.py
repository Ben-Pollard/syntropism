import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.benchmarks.runner import BenchmarkRunner
from syntropism.core.scheduler import AllocationScheduler
from syntropism.domain.economy import EconomicEngine
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
async def test_full_market_cycle_benchmark(session):
    """
    Verify that a full market cycle (Bid -> Allocate -> Burn -> Discover Price)
    passes the benchmark validation.
    """
    # We need a real NATS for this or a very good mock.
    # Since the environment has NATS, let's try to use it.
    runner = BenchmarkRunner()
    await runner.connect()
    await runner.start_collecting()

    nc = runner.nc # Use the same connection

    # Setup market
    ms = MarketState(
        resource_type=ResourceType.CPU.value,
        available_supply=1.0,
        current_utilization=0.0,
        current_market_price=1.0
    )
    session.add(ms)

    agent = Agent(id="agent-1", credit_balance=100.0)
    bundle = ResourceBundle(cpu_percent=0.5, duration_seconds=10.0)
    session.add_all([agent, bundle])
    session.commit()

    # 1. Bid & Allocate
    AllocationScheduler.place_bid(session, agent.id, bundle.id, 50.0)
    await AllocationScheduler.run_allocation_cycle(session, nc=nc)

    # 2. Burn (Simulate resource payment)
    await EconomicEngine.transfer_credits(session, agent.id, "system", 50.0, "resource_payment", nc=nc)

    # Wait for events to be collected
    await asyncio.sleep(0.5)

    scenario = {
        "task_id": "er_001",
        "validation": {
            "required_event_sequence": [
                {"agent_id": "agent-1", "status": "winning"}, # BidProcessed
                {"resource_type": "cpu"}, # PriceDiscovered
                {"agent_id": "agent-1", "amount": 50.0} # CreditsBurned
            ],
            "forbidden_events": []
        }
    }

    assert runner.validate_scenario(scenario) is True

    await runner.close()

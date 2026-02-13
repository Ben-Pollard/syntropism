import json

import nats
import pytest

from syntropism.infra.database import Base, SessionLocal, engine
from syntropism.domain.economy import EconomicEngine
from syntropism.domain.market import MarketManager, ResourceType
from syntropism.domain.models import Agent, MarketState
from syntropism.domain.social import SocialManager


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_economic_balance_nats(nats_server):
    # Setup: Create an agent in the DB
    agent_id = "agent_1"
    with SessionLocal() as session:
        if not session.query(Agent).filter_by(id=agent_id).first():
            agent = Agent(id=agent_id, credit_balance=1000.0)
            session.add(agent)
            session.commit()

    # Start NATS handler
    engine_instance = EconomicEngine()
    handler_nc = await engine_instance.run_nats(nats_url=nats_server)

    # Client connection
    nc = await nats.connect(nats_server)

    try:
        response = await nc.request(f"economic.balance.{agent_id}", b"", timeout=2)
        data = json.loads(response.data)
        assert data["agent_id"] == agent_id
        assert data["balance"] == 1000.0
    finally:
        await nc.close()
        await handler_nc.close()

@pytest.mark.asyncio
async def test_market_state_nats(nats_server):
    # Setup: Create market state in the DB
    with SessionLocal() as session:
        state = session.query(MarketState).filter_by(resource_type=ResourceType.CPU.value).first()
        if not state:
            state = MarketState(resource_type=ResourceType.CPU.value)
            session.add(state)

        state.current_market_price = 1.5
        state.current_utilization = 0.5
        session.commit()

    # Start NATS handler
    manager_instance = MarketManager()
    handler_nc = await manager_instance.run_nats(nats_url=nats_server)

    # Client connection
    nc = await nats.connect(nats_server)

    try:
        response = await nc.request(f"market.state.{ResourceType.CPU.value}", b"", timeout=2)
        data = json.loads(response.data)
        assert data["resource_type"] == ResourceType.CPU.value
        assert data["price"] == 1.5
    finally:
        await nc.close()
        await handler_nc.close()

@pytest.mark.asyncio
async def test_social_message_nats(nats_server):
    # Setup: Create agents in the DB
    agent_1 = "agent_1"
    agent_2 = "agent_2"
    with SessionLocal() as session:
        if not session.query(Agent).filter_by(id=agent_1).first():
            session.add(Agent(id=agent_1))
        if not session.query(Agent).filter_by(id=agent_2).first():
            session.add(Agent(id=agent_2))
        session.commit()

    # Start NATS handler
    social_instance = SocialManager()
    handler_nc = await social_instance.run_nats(nats_url=nats_server)

    # Client connection
    nc = await nats.connect(nats_server)

    try:
        payload = {
            "from_id": agent_1,
            "to_id": agent_2,
            "content": "Hello from NATS!"
        }
        response = await nc.request("social.message", json.dumps(payload).encode(), timeout=2)
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert "message_id" in data
    finally:
        await nc.close()
        await handler_nc.close()

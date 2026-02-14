import enum
import json

import nats
from sqlalchemy.orm import Session

from syntropism.domain.models import MarketState, ResourceBundle
from syntropism.infra.database import SessionLocal


class ResourceType(enum.Enum):
    CPU = "cpu"
    MEMORY = "memory"
    TOKENS = "tokens"
    ATTENTION = "attention"


class MarketManager:
    MIN_PRICE = 0.01
    MAX_PRICE = 1000.0
    HIGH_UTILIZATION_THRESHOLD = 0.8
    LOW_UTILIZATION_THRESHOLD = 0.2
    PRICE_INCREASE_FACTOR = 0.1  # 10% increase for high utilization
    PRICE_DECREASE_FACTOR = 0.05  # 5% decrease for low utilization

    @staticmethod
    def update_prices(session: Session):
        """
        Prices are now discovered during the allocation cycle in the scheduler.
        This method now only ensures prices stay within bounds if needed,
        but the formulaic increase/decrease is removed.
        """
        states = session.query(MarketState).all()
        for state in states:
            # Clamp prices
            state.current_market_price = max(
                MarketManager.MIN_PRICE, min(MarketManager.MAX_PRICE, state.current_market_price)
            )

    @staticmethod
    def get_market_state(session: Session, resource_type: ResourceType) -> MarketState:
        return session.query(MarketState).filter_by(resource_type=resource_type.value).first()

    async def run_nats(self, nats_url: str = "nats://localhost:4222"):
        nc = await nats.connect(nats_url, connect_timeout=2)

        async def market_state_handler(msg):
            subject = msg.subject
            resource_type_str = subject.split(".")[-1]
            try:
                resource_type = ResourceType(resource_type_str)
                with SessionLocal() as session:
                    state = self.get_market_state(session, resource_type)
                    if state:
                        response = {
                            "resource_type": state.resource_type,
                            "price": state.current_market_price,
                            "utilization": state.current_utilization
                        }
                        await msg.respond(json.dumps(response).encode())
                    else:
                        await msg.respond(json.dumps({"error": "Resource type not found"}).encode())
            except ValueError:
                await msg.respond(json.dumps({"error": "Invalid resource type"}).encode())

        async def market_bid_handler(msg):
            from syntropism.core.scheduler import AllocationScheduler
            data = json.loads(msg.data)
            with SessionLocal() as session:
                try:
                    # Create bundle if not provided
                    bundle_id = data.get("bundle_id")
                    if not bundle_id:
                        bundle = ResourceBundle(
                            cpu_seconds=data.get("cpu_seconds", 0.0),
                            memory_mb=data.get("memory_mb", 0.0),
                            tokens=data.get("tokens", 0),
                            attention_share=data.get("attention_share", 0.0),
                        )
                        session.add(bundle)
                        session.flush()
                        bundle_id = bundle.id

                    bid = AllocationScheduler.place_bid(
                        session,
                        data["agent_id"],
                        bundle_id,
                        data["amount"]
                    )
                    await msg.respond(json.dumps({"status": "success", "bid_id": bid.id}).encode())
                except Exception as e:
                    await msg.respond(json.dumps({"status": "error", "message": str(e)}).encode())

        await nc.subscribe("market.state.*", cb=market_state_handler)
        await nc.subscribe("market.bid", cb=market_bid_handler)
        return nc

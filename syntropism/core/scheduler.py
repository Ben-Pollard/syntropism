from sqlalchemy.orm import Session

from syntropism.core.observability import inject_context, setup_tracing
from syntropism.domain.market import ResourceType
from syntropism.domain.models import Agent, Bid, BidStatus, Execution, MarketState, ResourceBundle

# Initialize OTEL
tracer = setup_tracing("scheduler")


class AllocationScheduler:
    LLM_SPEND_LIMIT = 10000  # 100% capacity for tokens

    @staticmethod
    async def place_bid(session: Session, agent_id: str, bundle_id: str, amount: float, nc=None) -> Bid:
        from syntropism.domain.events import BidPlaced

        agent = session.query(Agent).filter_by(id=agent_id).first()
        if not agent:
            raise ValueError("Agent not found")

        bundle = session.query(ResourceBundle).filter_by(id=bundle_id).first()
        if not bundle:
            raise ValueError("Bundle not found")

        if agent.credit_balance < amount:
            raise ValueError("Insufficient credits")

        bid = Bid(from_agent_id=agent_id, resource_bundle_id=bundle_id, amount=amount, status=BidStatus.PENDING)
        session.add(bid)
        session.commit()

        if nc:
            event = BidPlaced(agent_id=agent_id, amount=amount, resource_bundle_id=bundle_id)
            headers = {}
            inject_context(headers)
            await nc.publish("system.market.bid_placed", event.model_dump_json().encode(), headers=headers)

        return bid

    @staticmethod
    def get_history(session: Session, agent_id: str) -> list[Bid]:
        return session.query(Bid).filter_by(from_agent_id=agent_id).order_by(Bid.timestamp.desc()).all()

    @staticmethod
    async def run_allocation_cycle(session: Session, nc=None):
        from syntropism.domain.events import BidProcessed, BidRejected, PriceDiscovered

        pending_bids = session.query(Bid).filter_by(status=BidStatus.PENDING).all()

        # Sort by price (highest first)
        pending_bids.sort(key=lambda x: x.amount, reverse=True)

        # Track supply per resource type
        market_states_objs = session.query(MarketState).all()
        market_states = {ms.resource_type: ms.available_supply for ms in market_states_objs}
        consumed_supply = dict.fromkeys(market_states, 0.0)

        # Track winning bids for price discovery
        # {resource_type: {"total_credits": 0.0, "total_capacity_seconds": 0.0}}
        price_discovery = {rt.value: {"total_credits": 0.0, "total_capacity_seconds": 0.0} for rt in ResourceType}

        for bid in pending_bids:
            bundle = bid.resource_bundle

            # Check all resource requirements (Capacity-Based)
            # Fallback to old fields if new ones are not set (for backward compatibility)
            requirements = {
                ResourceType.CPU.value: bundle.cpu_percent or (bundle.cpu_seconds / 10.0 if bundle.cpu_seconds else 0.0),
                ResourceType.MEMORY.value: bundle.memory_percent or (bundle.memory_mb / 1024.0 if bundle.memory_mb else 0.0),
                ResourceType.TOKENS.value: bundle.tokens_percent or (bundle.tokens / 1000000.0 if bundle.tokens else 0.0),
                ResourceType.ATTENTION.value: bundle.attention_percent or (bundle.attention_share or 0.0),
            }

            can_allocate = True
            for rt, req in requirements.items():
                if req is not None and req > 0 and rt in market_states:
                    if consumed_supply[rt] + req > market_states[rt]:
                        can_allocate = False
                        break

            # Also check if agent has enough credits (re-verify during cycle)
            if can_allocate and bid.agent.credit_balance < bid.amount:
                can_allocate = False

            if can_allocate:
                # Create Execution record
                execution = Execution(
                    agent_id=bid.from_agent_id, resource_bundle_id=bid.resource_bundle_id, status="PENDING"
                )
                session.add(execution)
                session.flush()  # To get execution.id

                bid.execution_id = execution.id
                bid.status = BidStatus.WINNING
                bid.agent.credit_balance -= bid.amount

                # Increment consumed supply for all relevant resources
                for rt, req in requirements.items():
                    if req is not None and req > 0 and rt in market_states:
                        consumed_supply[rt] += req
                        # Track for price discovery
                        price_discovery[rt]["total_credits"] += bid.amount
                        price_discovery[rt]["total_capacity_seconds"] += req * bundle.duration_seconds
            else:
                bid.status = BidStatus.OUTBID
                if nc:
                    reject_event = BidRejected(
                        agent_id=bid.from_agent_id, reason="Insufficient supply or credits during allocation cycle"
                    )
                    headers = {}
                    inject_context(headers)
                    await nc.publish("system.market.bid_rejected", reject_event.model_dump_json().encode(), headers=headers)

            # Emit event
            if nc:
                event = BidProcessed(
                    bid_id=bid.id,
                    agent_id=bid.from_agent_id,
                    amount=bid.amount,
                    status=bid.status.value,
                    resource_bundle_id=bid.resource_bundle_id,
                )
                headers = {}
                inject_context(headers)
                await nc.publish("system.market.bid_processed", event.model_dump_json().encode(), headers=headers)

        # Update MarketState utilization and price in DB
        for ms in market_states_objs:
            ms.current_utilization = consumed_supply.get(ms.resource_type, 0.0)

            # Price Discovery
            discovery = price_discovery.get(ms.resource_type)
            if discovery and discovery["total_capacity_seconds"] > 0:
                ms.current_market_price = discovery["total_credits"] / discovery["total_capacity_seconds"]

                # Emit event
                if nc:
                    event = PriceDiscovered(
                        resource_type=ms.resource_type,
                        new_price=ms.current_market_price,
                        utilization=ms.current_utilization,
                    )
                    headers = {}
                    inject_context(headers)
                    await nc.publish("system.market.price_discovered", event.model_dump_json().encode(), headers=headers)

        session.commit()

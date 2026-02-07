from sqlalchemy.orm import Session

from .market import ResourceType
from .models import Agent, Bid, BidStatus, Execution, MarketState, ResourceBundle


class AllocationScheduler:
    @staticmethod
    def place_bid(session: Session, agent_id: str, bundle_id: str, amount: float) -> Bid:
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
        return bid

    @staticmethod
    def run_allocation_cycle(session: Session):
        pending_bids = session.query(Bid).filter_by(status=BidStatus.PENDING).all()

        # Sort by price (highest first)
        pending_bids.sort(key=lambda x: x.amount, reverse=True)

        allocated_bundles = set()

        # Track supply per resource type
        market_states = {ms.resource_type: ms.available_supply for ms in session.query(MarketState).all()}
        consumed_supply = dict.fromkeys(market_states, 0.0)

        for bid in pending_bids:
            if bid.resource_bundle_id in allocated_bundles:
                bid.status = BidStatus.OUTBID
                continue

            bundle = bid.resource_bundle

            # Check all resource requirements
            requirements = {
                ResourceType.CPU.value: bundle.cpu_seconds,
                ResourceType.MEMORY.value: bundle.memory_mb,
                ResourceType.TOKENS.value: bundle.tokens,
                ResourceType.ATTENTION.value: bundle.attention_share,
            }

            can_allocate = True
            for rt, req in requirements.items():
                if req > 0 and rt in market_states:
                    if consumed_supply[rt] + req > market_states[rt]:
                        can_allocate = False
                        break

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
                allocated_bundles.add(bid.resource_bundle_id)

                # Increment consumed supply for all relevant resources
                for rt, req in requirements.items():
                    if rt in market_states:
                        consumed_supply[rt] += req
            else:
                bid.status = BidStatus.OUTBID

        session.commit()

import json

import nats
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.orm import Session

from syntropism.domain.models import Agent, Transaction
from syntropism.infra.database import SessionLocal

# Initialize OTEL
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)


class EconomicEngine:
    """
    Engine for managing agent economies, including credit transfers and balance tracking.
    """

    @staticmethod
    async def transfer_credits(session: Session, from_id: str, to_id: str, amount: float, memo: str, nc=None):
        """
        Transfer credits from one agent to another.
        """
        from syntropism.domain.events import CreditsBurned

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Lock rows for update to prevent race conditions
        from_agent = session.query(Agent).filter(Agent.id == from_id).with_for_update().first()
        to_agent = None
        if to_id != "system":
            to_agent = session.query(Agent).filter(Agent.id == to_id).with_for_update().first()

        if not from_agent:
            raise ValueError(f"Source agent {from_id} not found")
        if to_id != "system" and not to_agent:
            raise ValueError(f"Destination agent {to_id} not found")

        if from_agent.credit_balance < amount:
            raise ValueError("Insufficient funds")

        # Update balances
        from_agent.credit_balance -= amount
        from_agent.total_credits_spent += amount

        if to_agent:
            to_agent.credit_balance += amount
            to_agent.total_credits_earned += amount

        # Record transaction
        transaction = Transaction(from_entity_id=from_id, to_entity_id=to_id, amount=amount, memo=memo)
        session.add(transaction)

        # Emit event if burning (transfer to system/null)
        if nc and (to_id is None or to_id == "system"):
            event = CreditsBurned(agent_id=from_id, amount=amount, reason=memo)
            await nc.publish("system.economy.credits_burned", event.model_dump_json().encode())

    @staticmethod
    def get_balance(session: Session, agent_id: str) -> float:
        """
        Get the current credit balance of an agent.
        """
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.credit_balance

    @staticmethod
    def get_history(session: Session, entity_id: str) -> list[Transaction]:
        """
        Get the transaction history for an agent.
        """
        return (
            session.query(Transaction)
            .filter((Transaction.from_entity_id == entity_id) | (Transaction.to_entity_id == entity_id))
            .order_by(Transaction.timestamp.desc())
            .all()
        )

    async def run_nats(self, nats_url: str = "nats://localhost:4222"):
        nc = await nats.connect(nats_url, connect_timeout=2)

        async def balance_handler(msg):
            with tracer.start_as_current_span("balance_handler") as span:
                subject = msg.subject
                agent_id = subject.split(".")[-1]
                span.set_attribute("agent_id", agent_id)

                with SessionLocal() as session:
                    try:
                        balance = self.get_balance(session, agent_id)
                        response = {"agent_id": agent_id, "balance": balance}
                        await msg.respond(json.dumps(response).encode())
                    except ValueError as e:
                        span.record_exception(e)
                        await msg.respond(json.dumps({"error": str(e)}).encode())

        await nc.subscribe("economic.balance.*", cb=balance_handler)
        return nc

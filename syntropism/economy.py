from sqlalchemy.orm import Session

from .models import Agent, Transaction


class EconomicEngine:
    """
    Engine for managing agent economies, including credit transfers and balance tracking.
    """

    @staticmethod
    def transfer_credits(session: Session, from_id: str, to_id: str, amount: float, memo: str):
        """
        Transfer credits from one agent to another.

        This operation performs balance checks and updates both agents' balances and
        total earned/spent statistics. It also records a transaction.

        Note: This method does NOT call session.commit(). The caller is responsible
        for committing the transaction to allow for composability.

        Args:
            session: SQLAlchemy session
            from_id: ID of the source agent
            to_id: ID of the destination agent
            amount: Amount of credits to transfer (must be positive)
            memo: Description of the transaction

        Raises:
            ValueError: If amount is non-positive, agents are not found, or source has insufficient funds.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Lock rows for update to prevent race conditions
        from_agent = session.query(Agent).filter(Agent.id == from_id).with_for_update().first()
        to_agent = session.query(Agent).filter(Agent.id == to_id).with_for_update().first()

        if not from_agent:
            raise ValueError(f"Source agent {from_id} not found")
        if not to_agent:
            raise ValueError(f"Destination agent {to_id} not found")

        if from_agent.credit_balance < amount:
            raise ValueError("Insufficient funds")

        # Update balances
        from_agent.credit_balance -= amount
        from_agent.total_credits_spent += amount

        to_agent.credit_balance += amount
        to_agent.total_credits_earned += amount

        # Record transaction
        transaction = Transaction(from_entity_id=from_id, to_entity_id=to_id, amount=amount, memo=memo)
        session.add(transaction)

    @staticmethod
    def get_balance(session: Session, agent_id: str) -> float:
        """
        Get the current credit balance of an agent.

        Args:
            session: SQLAlchemy session
            agent_id: ID of the agent

        Returns:
            The current credit balance

        Raises:
            ValueError: If the agent is not found
        """
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.credit_balance

    @staticmethod
    def get_history(session: Session, entity_id: str) -> list[Transaction]:
        """
        Get the transaction history for an agent.

        Args:
            session: SQLAlchemy session
            entity_id: ID of the agent

        Returns:
            List of Transaction objects involving the agent, ordered by timestamp descending.
        """
        return (
            session.query(Transaction)
            .filter((Transaction.from_entity_id == entity_id) | (Transaction.to_entity_id == entity_id))
            .order_by(Transaction.timestamp.desc())
            .all()
        )

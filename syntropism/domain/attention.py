from sqlalchemy.orm import Session

from syntropism.domain.models import Agent, Execution, Prompt, PromptStatus, Response, Transaction

# Default conversion rates from docs/design/monolith_spec.md
ATTENTION_CONVERSION_RATES = {"interesting": 50.0, "useful": 50.0, "understandable": 50.0}


class AttentionManager:
    @staticmethod
    def submit_prompt(session: Session, agent_id: str, execution_id: str, content: dict, bid_amount: float) -> Prompt:
        if bid_amount < 0:
            raise ValueError("Bid amount must be non-negative")

        # Fetch the Execution by execution_id
        execution = session.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        # Check execution.resource_bundle.attention_share > 0
        if not (execution.resource_bundle and execution.resource_bundle.attention_share > 0):
            raise ValueError("Agent does not have attention allocation for this execution")

        # Lock agent for update to prevent race conditions
        agent = session.query(Agent).filter(Agent.id == agent_id).with_for_update().first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if agent.credit_balance < bid_amount:
            raise ValueError("Insufficient funds")

        # Deduct bid amount immediately (escrow)
        agent.credit_balance -= bid_amount
        agent.total_credits_spent += bid_amount

        # Record transaction for the bid (to escrow)
        transaction = Transaction(
            from_entity_id=agent_id, to_entity_id="attention_escrow", amount=bid_amount, memo="Bid for attention slot"
        )
        session.add(transaction)

        prompt = Prompt(
            from_agent_id=agent_id,
            execution_id=execution_id,
            content=content,
            bid_amount=bid_amount,
            status=PromptStatus.PENDING,
        )
        session.add(prompt)
        return prompt

    @staticmethod
    def get_pending_prompts(session: Session) -> list[Prompt]:
        return (
            session.query(Prompt).filter(Prompt.status == PromptStatus.PENDING).order_by(Prompt.bid_amount.desc()).all()
        )

    @staticmethod
    def reward_prompt(
        session: Session, prompt_id: str, interesting: float, useful: float, understandable: float, reason: str = None
    ) -> Response:
        # Validate scores
        for _score_name, score_value in [
            ("interesting", interesting),
            ("useful", useful),
            ("understandable", understandable),
        ]:
            if not (0 <= score_value <= 10):
                raise ValueError("Scores must be between 0 and 10")

        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).with_for_update().first()
        if not prompt:
            raise ValueError(f"Prompt {prompt_id} not found")

        if prompt.status == PromptStatus.RESPONDED:
            raise ValueError(f"Prompt {prompt_id} already responded")

        # Mark as ACTIVE before responding (as per spec lifecycle)
        prompt.status = PromptStatus.ACTIVE
        session.flush()

        # Calculate credits based on conversion rates
        credits_awarded = (
            interesting * ATTENTION_CONVERSION_RATES["interesting"]
            + useful * ATTENTION_CONVERSION_RATES["useful"]
            + understandable * ATTENTION_CONVERSION_RATES["understandable"]
        )

        # Create response
        response = Response(
            prompt_id=prompt_id,
            interesting=interesting,
            useful=useful,
            understandable=understandable,
            reason=reason,
            credits_awarded=credits_awarded,
        )
        session.add(response)

        # Award credits to agent
        agent = session.query(Agent).filter(Agent.id == prompt.from_agent_id).with_for_update().first()
        if not agent:
            raise ValueError(f"Agent {prompt.from_agent_id} not found")

        agent.credit_balance += credits_awarded
        agent.total_credits_earned += credits_awarded

        # Record transaction for the reward (from human)
        reward_transaction = Transaction(
            from_entity_id="human", to_entity_id=agent.id, amount=credits_awarded, memo=f"Reward for prompt {prompt_id}"
        )
        session.add(reward_transaction)

        # Transfer escrowed credits to system account (finalizing the bid payment)
        escrow_transaction = Transaction(
            from_entity_id="attention_escrow",
            to_entity_id="system",
            amount=prompt.bid_amount,
            memo=f"Finalized bid payment for prompt {prompt_id}",
        )
        session.add(escrow_transaction)

        # Update prompt status
        prompt.status = PromptStatus.RESPONDED

        return response


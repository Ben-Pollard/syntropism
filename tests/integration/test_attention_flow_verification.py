"""
Integration Test: End-to-End Attention Flow

This test verifies the complete attention loop without requiring a running Docker daemon.
It mocks the ExecutionSandbox to simulate agent execution and verifies the database state.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from syntropism.attention import AttentionManager
from syntropism.database import Base
from syntropism.genesis import create_genesis_agent
from syntropism.models import Execution, PromptStatus, ResourceBundle
from syntropism.scheduler import AllocationScheduler


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(db_engine):
    """Create a new database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.integration
def test_full_attention_flow(session: Session):
    """
    Test the full lifecycle: Bootstrap -> Bid -> Execution -> Prompt -> Reward.
    """
    # 1. Bootstrap System
    agent = create_genesis_agent(session)
    print(f"Created agent: {agent.id}")

    # Create a resource bundle with attention_share=1.0
    bundle = ResourceBundle(
        cpu_seconds=1.0,
        memory_mb=128.0,
        tokens=1000,
        attention_share=1.0,
    )
    session.add(bundle)
    session.flush()

    # Create a bid
    bid = AllocationScheduler.place_bid(session, agent.id, bundle.id, 10.0)
    print(f"Created bid: {bid.id}")

    # Run allocation cycle (manual trigger)
    AllocationScheduler.run_allocation_cycle(session)
    session.refresh(bid)

    assert bid.status.value == "winning", "Bid should be winning"
    assert bid.execution_id is not None, "Bid should have execution ID"

    execution = session.query(Execution).filter(Execution.id == bid.execution_id).first()
    assert execution is not None

    # 2. Simulate Agent Execution (Mock Sandbox)
    # In a real run, this would be `sandbox.run_agent(...)`.
    # Here we simulate the agent successfully completing and submitting a prompt.
    # The agent would read env.json, set AGENT_ID, and call AttentionManager.

    # We act "as if" the agent called the API by invoking the manager directly
    # with the data it would have sent.
    prompt_content = {"text": "Hello, I am Genesis. I have executed successfully."}

    # Submit prompt
    prompt = AttentionManager.submit_prompt(
        session=session,
        agent_id=agent.id,
        execution_id=execution.id,
        content=prompt_content,
        bid_amount=5.0
    )

    session.flush() # Ensure ID is generated
    assert prompt.id is not None
    assert prompt.status == PromptStatus.PENDING
    print(f"Created prompt: {prompt.id}")

    # 3. Verify Orchestrator Loop
    # We verify that get_pending_prompts returns our prompt
    pending_prompts = AttentionManager.get_pending_prompts(session)
    assert len(pending_prompts) == 1
    assert pending_prompts[0].id == prompt.id

    # 4. Simulate Human Reward
    # The orchestrator would ask the human for scores.
    response = AttentionManager.reward_prompt(
        session=session,
        prompt_id=prompt.id,
        interesting=9.0,
        useful=8.0,
        understandable=10.0,
        reason="The agent demonstrated clear understanding."
    )

    session.commit() # Ensure the state is committed to the DB session

    assert response.credits_awarded > 0
    session.refresh(prompt)
    assert prompt.status == PromptStatus.RESPONDED

    # Verify agent received credits
    session.refresh(agent)
    assert agent.total_credits_earned > 0

    print(f"Agent {agent.id} earned {response.credits_awarded} credits.")
    print("End-to-end attention flow verified successfully.")

#!/usr/bin/env python
"""
Monolithic Orchestrator for the Evolutionary Agent Economy System.

This module initializes the system and runs the main control loop that:
1. Initializes the database and seeds initial state
2. Creates the Genesis agent if needed
3. Runs the system loop for allocation, execution, market updates, and attention
4. Bootstraps the system if no completed bids exist
"""

import os
import sys
import threading

import uvicorn

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session

from syntropism.database import Base, SessionLocal, engine
from syntropism.genesis import create_genesis_agent
from syntropism.market import ResourceType
from syntropism.models import Agent, Bid, BidStatus, MarketState, ResourceBundle
from syntropism.orchestrator import run_system_loop


def init_db():
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")


def seed_market_state(session: Session):
    """Seed the market state with initial resources if empty."""
    # Check if market states already exist
    existing = session.query(MarketState).first()
    if existing:
        print("Market state already seeded.")
        return

    resources = [
        (ResourceType.CPU.value, 10.0, 1.0),
        (ResourceType.MEMORY.value, 1024.0, 0.1),
        (ResourceType.TOKENS.value, 1000000.0, 0.001),
        (ResourceType.ATTENTION.value, 1.0, 10.0),
    ]

    for resource_type, supply, price in resources:
        ms = MarketState(
            resource_type=resource_type,
            available_supply=supply,
            current_market_price=price,
            current_utilization=0.0,
        )
        session.add(ms)

    session.commit()
    print(f"Seeded {len(resources)} market resources.")


def seed_genesis_agent(session: Session) -> Agent:
    """Create the Genesis agent if it doesn't exist."""
    # Check if genesis agent already exists
    genesis = session.query(Agent).filter_by(id="genesis").first()
    if genesis:
        print(f"Genesis agent already exists (id={genesis.id}).")
        return genesis

    # Create genesis agent with 1000 credits
    agent = create_genesis_agent(session)
    print(f"Created Genesis agent with id={agent.id} and {agent.credit_balance} credits.")
    return agent


def check_completed_bids(session: Session) -> bool:
    """Check if any COMPLETED bids exist in the system."""
    completed = session.query(Bid).filter_by(status=BidStatus.COMPLETED).first()
    return completed is not None


def bootstrap_genesis_execution(session: Session):
    """
    Bootstrap the system by manually triggering Genesis agent execution.

    This creates a winning bid and execution for the Genesis agent to start the cycle.
    """
    print("Bootstrapping system - no completed bids found.")

    # Get genesis agent
    genesis = session.query(Agent).filter_by(id="genesis").first()
    if not genesis:
        print("ERROR: Genesis agent not found. Please run seed first.")
        return

    # Create a resource bundle for genesis (minimal resources with attention)
    bundle = ResourceBundle(
        cpu_seconds=5.0,
        memory_mb=128.0,
        tokens=1000,
        attention_share=1.0,  # Allocate full attention to enable human prompting
    )
    session.add(bundle)
    session.flush()

    # Create a bid from genesis agent
    bid_amount = 10.0  # Minimal bid to get resources
    bid = Bid(
        from_agent_id=genesis.id,
        resource_bundle_id=bundle.id,
        amount=bid_amount,
        status=BidStatus.WINNING,  # Mark as winning directly for bootstrap
    )
    session.add(bid)

    # Create execution record
    from syntropism.models import Execution

    execution = Execution(
        agent_id=genesis.id,
        resource_bundle_id=bundle.id,
        status="PENDING",
    )
    session.add(execution)
    session.flush()

    bid.execution_id = execution.id
    genesis.credit_balance -= bid_amount

    session.commit()
    print("Bootstrap: Created bid and execution for Genesis agent.")


def main():
    """Main entry point for the monolithic orchestrator."""
    print("=" * 60)
    print("Evolutionary Agent Economy System - Monolithic Orchestrator")
    print("=" * 60)

    # Step 1: Initialize database
    print("\n[1/4] Initializing database...")
    init_db()

    # Get a session
    session = SessionLocal()

    try:
        # Step 2: Seed market state
        print("\n[2/4] Seeding market state...")
        seed_market_state(session)

        # Step 3: Create genesis agent
        print("\n[3/4] Creating Genesis agent...")
        seed_genesis_agent(session)

        # Step 4: Bootstrap if needed and run system loop
        print("\n[4/4] Running system loop...")

        # Check if bootstrap is needed
        if not check_completed_bids(session):
            bootstrap_genesis_execution(session)

        # Run the main system loop
        import time

        from syntropism.service import app

        continuous = os.getenv("CONTINUOUS") == "1"

        # Start API server in background
        def run_api():
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        print("API Server started on port 8000.")

        while True:
            print("\n--- Starting System Loop ---")
            # Refresh session to ensure we have latest state from DB
            session.expire_all()
            run_system_loop(session)
            print("--- System Loop Complete ---")

            if not continuous:
                break
            time.sleep(5)

    finally:
        session.close()


if __name__ == "__main__":
    main()

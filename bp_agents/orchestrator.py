import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .attention import AttentionManager
from .market import MarketManager
from .models import Bid, BidStatus, Execution, Workspace
from .sandbox import ExecutionSandbox
from .scheduler import AllocationScheduler


def run_system_loop(session: Session):
    """
    Main system loop that orchestrates the agent economy.

    Steps:
    1. Allocation: Run allocation cycle to assign resources to winning bids
    2. Execution: Execute all winning bids
    3. Market Update: Adjust prices based on utilization
    4. Attention: Process pending prompts and collect human scores
    """
    # Step 1: Allocation
    AllocationScheduler.run_allocation_cycle(session)

    # Step 2: Execution - find all WINNING bids and execute them
    winning_bids = session.query(Bid).filter_by(status=BidStatus.WINNING).all()

    for bid in winning_bids:
        agent = bid.agent
        workspace = session.query(Workspace).filter_by(agent_id=agent.id).first()

        if not workspace:
            continue

        workspace_path = workspace.filesystem_path

        # Create env.json with execution context
        env_data = {
            "agent_id": agent.id,
            "credits": agent.credit_balance,
            "execution_id": bid.execution_id,
        }
        env_json_path = os.path.join(workspace_path, "env.json")
        with open(env_json_path, "w") as f:
            json.dump(env_data, f, indent=2)

        # Run the agent in sandbox
        sandbox = ExecutionSandbox()
        exit_code, logs = sandbox.run_agent(
            agent_id=agent.id,
            workspace_path=workspace_path,
            resource_bundle=bid.resource_bundle,
            runtime_data=env_data,
        )

        # Update bid status to COMPLETED
        bid.status = BidStatus.COMPLETED

        # Update execution record
        execution = session.query(Execution).filter_by(id=bid.execution_id).first()
        if execution:
            execution.status = "COMPLETED" if exit_code == 0 else "FAILED"
            execution.exit_code = exit_code
            execution.termination_reason = logs[:500] if logs else None
            execution.end_time = datetime.now(UTC)

    # Step 3: Market Update - adjust prices based on utilization
    MarketManager.update_prices(session)

    # Step 4: Attention - process pending prompts
    prompts = AttentionManager.get_pending_prompts(session)

    for prompt in prompts:
        # Print prompt content to terminal
        print(f"\n=== PROMPT FROM AGENT {prompt.from_agent_id} ===")
        if isinstance(prompt.content, dict):
            for key, value in prompt.content.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {prompt.content}")
        print("=" * 50)

        # Get scores from human
        while True:
            try:
                scores_input = input("Enter scores (interesting useful understandable) 0-10, separated by spaces: ")
                parts = scores_input.strip().split()
                if len(parts) == 3:
                    interesting, useful, understandable = float(parts[0]), float(parts[1]), float(parts[2])
                    if all(0 <= s <= 10 for s in [interesting, useful, understandable]):
                        break
                print("Invalid input. Please enter three numbers between 0 and 10.")
            except ValueError:
                print("Invalid input. Please enter numbers between 0 and 10.")

        # Reward the prompt
        AttentionManager.reward_prompt(
            session=session,
            prompt_id=prompt.id,
            interesting=interesting,
            useful=useful,
            understandable=understandable,
        )

    session.commit()

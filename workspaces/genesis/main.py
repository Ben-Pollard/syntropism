"""
Genesis Agent Logic

This module implements the Genesis agent's market participation logic,
including reading environment configuration, fetching market data,
placing bids, and prompting humans when allocated attention.

Refactored to use service layer abstractions instead of direct HTTP calls.
"""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

# Support both relative imports (when run as module) and absolute imports (when imported by tests)
try:
    from .services import (
        CognitionService,
        EconomicService,
        EvolutionService,
        SocialService,
        WorkspaceService,
    )
except ImportError:
    from services import (
        CognitionService,
        EconomicService,
        EvolutionService,
        SocialService,
        WorkspaceService,
    )


def load_env(env_path: str = None) -> dict | None:
    """
    Load environment configuration from env.json.

    Args:
        env_path: Path to the env.json file.
                  Defaults to /workspace/env.json (where sandbox writes it)
                  or /app/env.json (for direct execution)

    Returns:
        Dictionary containing agent_id, credits, and optionally attention_share
        Returns None if file doesn't exist
    """
    if env_path is None:
        # Try workspace path first (where sandbox writes it), then app path
        env_path = os.getenv("ENV_JSON_PATH", "/workspace/env.json")

    if not os.path.exists(env_path):
        return None

    with open(env_path) as f:
        return json.load(f)


def calculate_bid(balance: float, attention_share: float = 0.0) -> dict:
    """
    Calculate the bid amount and resource bundle.

    Logic:
    - Bid 10% of balance for a standard bundle (1 CPU, 128MB, 1000 tokens)
    - If balance > 500, also bid for attention_share=1.0

    Args:
        balance: The agent's current credit balance
        attention_share: The attention share allocation (0.0 or 1.0)

    Returns:
        Dictionary containing bid details:
        - amount: Bid amount (10% of balance)
        - cpu: CPU units (1)
        - memory_mb: Memory in MB (128)
        - tokens: Token allocation (1000)
        - attention_share: Attention share (0.0 or 1.0)
    """
    bid_amount = balance * 0.10  # 10% of balance

    return {"amount": bid_amount, "cpu": 1, "memory_mb": 128, "tokens": 1000, "attention_share": attention_share}


def main():
    """
    Main entry point for the Genesis agent.

    This function:
    1. Loads environment configuration from /app/env.json
    2. Initializes service layer abstractions
    3. Fetches market data and agent balance via services
    4. Calculates and places a bid based on balance
    5. Sends a prompt to the human if attention_share > 0
    """
    # Configure logging
    logger.add(sys.stderr, format="{time} {level} [component:agent-genesis] {message}", level="INFO")

    # Enable debugpy if DEBUG environment variable is set
    if os.getenv("DEBUG") == "1" or os.getenv("DEBUGPY_ENABLE") == "1":
        import debugpy

        debug_host = os.getenv("DEBUGPY_HOST", "0.0.0.0")
        debug_port = int(os.getenv("DEBUGPY_PORT", "5678"))
        logger.info(f"[component:agent-genesis] Starting debugpy server on {debug_host}:{debug_port}")
        debugpy.listen((debug_host, debug_port))
        logger.info("[component:agent-genesis] Waiting for debugger attach...")
        debugpy.wait_for_client()
        logger.info("[component:agent-genesis] Debugger attached!")

    # Step 1: Load environment configuration
    env = load_env()
    if env is None:
        env_path = os.getenv("ENV_JSON_PATH", "/workspace/env.json")
        print(f"Error: env.json not found at {env_path}")
        return

    agent_id = env.get("agent_id")
    credits = env.get("credits", 0.0)
    attention_share = env.get("attention_share", 0.0)

    print(f"Genesis Agent {agent_id} active.")
    print(f"Balance: {credits}")
    print(f"Attention Share: {attention_share}")

    # Initialize service layer abstractions
    cognition_service = CognitionService()
    economic_service = EconomicService()
    evolution_service = EvolutionService()
    social_service = SocialService()
    workspace_service = WorkspaceService()

    # Validate workspace path for audit logging
    workspace_path = os.getenv("WORKSPACE_PATH", "/workspace")
    try:
        workspace_service.validate_path(workspace_path)
        workspace_service.audit_log("agent_startup", workspace_path)
    except ValueError as e:
        logger.warning(f"Workspace path validation failed: {e}")

    try:
        # Step 2: Fetch market data via CognitionService (wrapper for deepagents)
        print("\nFetching market data via CognitionService...")
        cognition_result = cognition_service.integrate()
        print(f"Cognition integration: {cognition_result}")

        # Step 2: Fetch agent balance via EconomicService
        print("\nFetching agent balance via EconomicService...")
        # Use get_balance instead of place_bid for balance check
        try:
            balance_info = economic_service.get_balance()
            current_balance = balance_info.get("balance", credits)
        except Exception:
            current_balance = credits
        print(f"Current balance: {current_balance}")

        # Step 3: Calculate bid
        # If balance > 500, also bid for attention_share=1.0
        bid_attention = 1.0 if current_balance > 500 else 0.0
        bid = calculate_bid(current_balance, attention_share=bid_attention)

        print(f"\nPlacing bid via EconomicService: {bid}")
        bid_result = economic_service.place_bid(bid["amount"], resources=bid)
        print(f"EconomicService response: {bid_result}")

        # Step 4: Send prompt if attention_share > 0 via SocialService
        if attention_share > 0:
            print("\nSending prompt to human via SocialService...")
            prompt_content = {"text": "Hello from Genesis! I am evolving."}
            prompt_result = social_service.submit_prompt(content=prompt_content, bid_amount=bid["amount"])
            print(f"SocialService response: {prompt_result}")
        else:
            print("\nNo attention allocated, skipping prompt.")

        # Step 5: Spawn child if balance is high
        if current_balance > 800:
            print("\nHigh balance detected, spawning child agent...")
            spawn_result = evolution_service.spawn_child(payload={"purpose": "exploration"})
            print(f"Spawn result: {spawn_result}")

        logger.info("Genesis agent execution completed successfully")

    except Exception as e:
        logger.error(f"Error during genesis agent execution: {e}")
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()

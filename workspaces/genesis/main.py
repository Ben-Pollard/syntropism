"""
Genesis Agent Logic

This module implements the Genesis agent's market participation logic,
including reading environment configuration, fetching market data,
placing bids, and prompting humans when allocated attention.
"""

import json
import os

import requests


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


def fetch_market_prices(base_url: str) -> dict:
    """
    Fetch current market prices from the market service.

    Args:
        base_url: Base URL of the market service (e.g., http://localhost:8000)

    Returns:
        Dictionary containing current market prices
    """
    response = requests.get(f"{base_url}/market/prices")
    response.raise_for_status()
    return response.json()


def fetch_balance(base_url: str, agent_id: str) -> dict:
    """
    Fetch the agent's current balance from the economic service.

    Args:
        base_url: Base URL of the economic service (e.g., http://localhost:8000)
        agent_id: The agent's unique identifier

    Returns:
        Dictionary containing the agent's balance
    """
    response = requests.get(f"{base_url}/economic/balance/{agent_id}")
    response.raise_for_status()
    return response.json()


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


def place_bid(base_url: str, agent_id: str, bid_data: dict) -> bool:
    """
    Place a bid on the market.

    Args:
        base_url: Base URL of the market service (e.g., http://localhost:8000)
        agent_id: The agent's unique identifier
        bid_data: Dictionary containing bid details

    Returns:
        True if bid was successful, False otherwise
    """
    payload = {"agent_id": agent_id, **bid_data}

    response = requests.post(f"{base_url}/market/bid", json=payload)
    return response.status_code == 200


def send_prompt(base_url: str, message: str, attention_share: float = 1.0) -> bool:
    """
    Send a prompt to the human when the agent has allocated attention.

    Args:
        base_url: Base URL of the human interaction service (e.g., http://localhost:8000)
        message: The message to send to the human
        attention_share: The attention share allocation (only send if > 0)

    Returns:
        True if prompt was sent successfully, False if attention_share is 0
    """
    if attention_share <= 0:
        return False

    payload = {"message": message}
    response = requests.post(f"{base_url}/human/prompt", json=payload)
    return response.status_code == 200


def main():
    """
    Main entry point for the Genesis agent.

    This function:
    1. Loads environment configuration from /app/env.json
    2. Fetches market prices and agent balance
    3. Calculates and places a bid based on balance
    4. Sends a prompt to the human if attention_share > 0
    """
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

    # Determine service URL from environment or use default
    base_url = os.getenv("SYSTEM_SERVICE_URL", "http://localhost:8000")

    try:
        # Step 2: Fetch market prices
        print("\nFetching market prices...")
        prices = fetch_market_prices(base_url)
        print(f"Market prices: {prices}")

        # Step 2: Fetch agent balance
        print("\nFetching agent balance...")
        balance_info = fetch_balance(base_url, agent_id)
        current_balance = balance_info.get("balance", credits)
        print(f"Current balance: {current_balance}")

        # Step 3: Calculate bid
        # If balance > 500, also bid for attention_share=1.0
        bid_attention = 1.0 if current_balance > 500 else 0.0
        bid = calculate_bid(current_balance, attention_share=bid_attention)

        print(f"\nPlacing bid: {bid}")
        bid_success = place_bid(base_url, agent_id, bid)
        if bid_success:
            print("Bid placed successfully!")
        else:
            print("Failed to place bid.")

        # Step 4: Send prompt if attention_share > 0
        if attention_share > 0:
            print("\nSending prompt to human...")
            prompt_message = "Hello from Genesis! I am evolving."
            prompt_success = send_prompt(base_url, prompt_message, attention_share)
            if prompt_success:
                print("Prompt sent successfully!")
            else:
                print("Failed to send prompt.")
        else:
            print("\nNo attention allocated, skipping prompt.")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to services at {base_url}")
        print("Make sure the market and economic services are running.")
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()

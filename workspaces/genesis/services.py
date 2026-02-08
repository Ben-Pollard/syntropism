"""
Service Layer Abstractions

This module provides service layer abstractions for the Genesis Agent refactor:
- CognitionService: wrapper stub for deepagents integration
- EconomicService: HTTP client for EconomicEngine with standardized place_bid() method
- SocialService: HTTP client for human interaction (attention/prompts)
- WorkspaceService: secure filesystem abstraction with path validation and audit logging

All services make real HTTP calls to the System API (http://system:8000 by default).
The agent imports shared contracts from /system to ensure API compatibility.
"""

import os
import sys

# Import shared contracts
try:
    # In Sandbox: /system/syntropism/contracts.py
    sys.path.insert(0, "/system")
    from syntropism.contracts import BidRequest, PromptRequest
except ModuleNotFoundError:
    # In Host (when running from project root)
    from syntropism.contracts import BidRequest, PromptRequest

import httpx
from loguru import logger

# System API base URL - set by the runtime
SYSTEM_SERVICE_URL = os.getenv("SYSTEM_SERVICE_URL", "http://system:8000")


class CognitionService:
    """Wrapper stub for deepagents integration."""

    def __init__(self):
        logger.info('CognitionService initialized')

    def integrate(self):
        """Stub implementation wrapping deepagents integration."""
        logger.debug('CognitionService.integrate called')
        return 'Cognition integration called'


class EconomicService:
    """HTTP client for EconomicEngine with standardized place_bid() method."""

    def __init__(self, base_url: str = SYSTEM_SERVICE_URL):
        self.base_url = base_url
        logger.info(f'EconomicService initialized with base_url: {base_url}')

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an HTTP request to the System API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}")

        try:
            with httpx.Client() as client:
                if method.upper() == "GET":
                    response = client.get(url)
                elif method.upper() == "POST":
                    response = client.post(url, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    def place_bid(self, amount: float, resources: dict = None) -> dict:
        """
        Place a bid using the EconomicEngine via HTTP.
        """
        agent_id = os.getenv("AGENT_ID")
        if not agent_id:
            raise ValueError("AGENT_ID environment variable not set")

        # Use shared schema for validation (optional)
        if resources is None:
            resources = {}

        req_data = {
            "agent_id": agent_id,
            "amount": amount,
            "cpu_seconds": resources.get("cpu", 0.0),
            "memory_mb": resources.get("memory", 0.0),
            "tokens": resources.get("tokens", 0),
            "attention_share": resources.get("attention_share", 0.0),
        }

        # Validate using the shared contract (will raise if invalid)
        BidRequest(**req_data)

        result = self._make_request("POST", "/market/bid", req_data)
        logger.info(f"Bid placed: {result}")
        return result

    def get_balance(self, agent_id: str = None) -> dict:
        """
        Get the agent's current balance via HTTP.
        """
        if not agent_id:
            agent_id = os.getenv("AGENT_ID")
        result = self._make_request("GET", f"/economic/balance/{agent_id}")
        logger.debug(f"Balance retrieved: {result}")
        return result


class SocialService:
    """HTTP client for human interaction (attention/prompts)."""

    def __init__(self, base_url: str = SYSTEM_SERVICE_URL):
        self.base_url = base_url
        logger.info(f'SocialService initialized with base_url: {base_url}')

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an HTTP request to the System API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}")

        try:
            with httpx.Client() as client:
                if method.upper() == "GET":
                    response = client.get(url)
                elif method.upper() == "POST":
                    response = client.post(url, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    def submit_prompt(
        self,
        content: dict,
        bid_amount: float,
        execution_id: str = None,
    ) -> dict:
        """
        Submit a prompt for human attention via HTTP.
        """
        agent_id = os.getenv("AGENT_ID")
        if not agent_id:
            raise ValueError("AGENT_ID environment variable not set")

        if not execution_id:
            execution_id = os.getenv("EXECUTION_ID")
        if not execution_id:
            raise ValueError("EXECUTION_ID environment variable not set")

        # Prepare data using the shared contract
        req_data = {
            "agent_id": agent_id,
            "execution_id": execution_id,
            "content": content,
            "bid_amount": bid_amount,
        }

        # Validate using the shared contract
        PromptRequest(**req_data)

        # Correct endpoint as per System API
        result = self._make_request("POST", "/human/prompt", req_data)
        logger.info(f"Prompt submitted: {result}")
        return result

    def send_async_message(self, message: str) -> str:
        """
        Send an asynchronous message for non-blocking human interaction.
        """
        logger.debug(f'SocialService.send_async_message called with message: {message}')
        return f'Async response for {message}'


class WorkspaceService:
    """Secure filesystem abstraction with path validation and audit logging."""

    def __init__(self):
        logger.info('WorkspaceService initialized')

    def validate_path(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks."""
        logger.debug(f'Validating path: {path}')
        if '..' in path:
            raise ValueError('Invalid path: directory traversal detected')
        return True

    def audit_log(self, action: str, path: str) -> None:
        """Log filesystem actions for audit purposes."""
        logger.info(f'Audit log - Action: {action}, Path: {path}')


# Structured Logging Configuration with component tagging
logger.add('system.log', format='{time} {level} [component:agent-genesis] {message}', level='DEBUG', rotation='10 MB')

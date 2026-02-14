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
    from syntropism.domain.contracts import BidRequest, PromptRequest
except ModuleNotFoundError:
    # In Host (when running from project root)
    from syntropism.domain.contracts import BidRequest, PromptRequest

import asyncio
import json

import nats
from loguru import logger

# System API base URL - set by the runtime
SYSTEM_SERVICE_URL = os.getenv("SYSTEM_SERVICE_URL", "http://system:8000")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")


class CognitionService:
    """Wrapper stub for deepagents integration."""

    def __init__(self):
        logger.info("CognitionService initialized")

    def integrate(self):
        """Stub implementation wrapping deepagents integration."""
        logger.debug("CognitionService.integrate called")
        return "Cognition integration called"


class EconomicService:
    """NATS client for EconomicEngine with standardized place_bid() method."""

    def __init__(self, nats_url: str = NATS_URL):
        self.nats_url = nats_url
        logger.info(f"EconomicService initialized with nats_url: {nats_url}")

    async def _make_request(self, subject: str, data: dict = None) -> dict:
        """Make a NATS request to the System API."""
        logger.debug(f"Making NATS request to {subject} with data: {data}")

        nc = await nats.connect(self.nats_url, connect_timeout=2)
        try:
            payload = json.dumps(data).encode() if data else b""
            response = await nc.request(subject, payload, timeout=2)
            return json.loads(response.data)
        finally:
            await nc.close()

    def place_bid(self, amount: float, resources: dict = None) -> dict:
        """
        Place a bid using the EconomicEngine via NATS.
        """
        agent_id = os.getenv("AGENT_ID")
        if not agent_id:
            raise ValueError("AGENT_ID environment variable not set")

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

        # Validate using the shared contract
        BidRequest(**req_data)

        # We use a helper to run the async request in a sync context if needed,
        # but ideally the agent should be async.
        # For now, we'll use asyncio.run if no loop is running, or run_until_complete.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # This is a problem if we are in a sync method called from async
                # But for now let's assume we can use a future or the agent is async.
                # If the agent is sync, we might need a separate thread or just use asyncio.run
                result = asyncio.run_coroutine_threadsafe(self._make_request("market.bid", req_data), loop).result()
            else:
                result = asyncio.run(self._make_request("market.bid", req_data))
        except RuntimeError:
            result = asyncio.run(self._make_request("market.bid", req_data))

        logger.info(f"Bid placed: {result}")
        return result

    def get_balance(self, agent_id: str = None) -> dict:
        """
        Get the agent's current balance via NATS.
        """
        if not agent_id:
            agent_id = os.getenv("AGENT_ID")

        subject = f"economic.balance.{agent_id}"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(self._make_request(subject), loop).result()
            else:
                result = asyncio.run(self._make_request(subject))
        except RuntimeError:
            result = asyncio.run(self._make_request(subject))

        logger.debug(f"Balance retrieved: {result}")
        return result


class SocialService:
    """NATS client for human interaction (attention/prompts)."""

    def __init__(self, nats_url: str = NATS_URL):
        self.nats_url = nats_url
        logger.info(f"SocialService initialized with nats_url: {nats_url}")

    async def _make_request(self, subject: str, data: dict = None) -> dict:
        """Make a NATS request to the System API."""
        logger.debug(f"Making NATS request to {subject} with data: {data}")

        nc = await nats.connect(self.nats_url, connect_timeout=2)
        try:
            payload = json.dumps(data).encode() if data else b""
            response = await nc.request(subject, payload, timeout=2)
            return json.loads(response.data)
        finally:
            await nc.close()

    def submit_prompt(
        self,
        content: dict,
        bid_amount: float,
        execution_id: str = None,
    ) -> dict:
        """
        Submit a prompt for human attention via NATS.
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

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(self._make_request("human.prompt", req_data), loop).result()
            else:
                result = asyncio.run(self._make_request("human.prompt", req_data))
        except RuntimeError:
            result = asyncio.run(self._make_request("human.prompt", req_data))

        logger.info(f"Prompt submitted: {result}")
        return result

    def send_async_message(self, message: str) -> str:
        """
        Send an asynchronous message for non-blocking human interaction.
        """
        logger.debug(f"SocialService.send_async_message called with message: {message}")

        agent_id = os.getenv("AGENT_ID")
        payload = {
            "from_id": agent_id,
            "to_id": "human",  # Default to human for now
            "content": message,
        }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._publish("social.message", payload), loop)
            else:
                asyncio.run(self._publish("social.message", payload))
        except RuntimeError:
            asyncio.run(self._publish("social.message", payload))

        return f"Async message sent: {message}"

    async def _publish(self, subject: str, data: dict):
        nc = await nats.connect(self.nats_url, connect_timeout=2)
        try:
            await nc.publish(subject, json.dumps(data).encode())
        finally:
            await nc.close()


class WorkspaceService:
    """Secure filesystem abstraction with path validation and audit logging."""

    def __init__(self):
        logger.info("WorkspaceService initialized")

    def validate_path(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks."""
        logger.debug(f"Validating path: {path}")
        if ".." in path:
            raise ValueError("Invalid path: directory traversal detected")
        return True

    def audit_log(self, action: str, path: str) -> None:
        """Log filesystem actions for audit purposes."""
        logger.info(f"Audit log - Action: {action}, Path: {path}")


class EvolutionService:
    """NATS client for agent evolution (spawning)."""

    def __init__(self, nats_url: str = NATS_URL):
        self.nats_url = nats_url
        logger.info(f"EvolutionService initialized with nats_url: {nats_url}")

    async def _make_request(self, subject: str, data: dict = None) -> dict:
        """Make a NATS request to the System API."""
        logger.debug(f"Making NATS request to {subject} with data: {data}")

        nc = await nats.connect(self.nats_url, connect_timeout=2)
        try:
            payload = json.dumps(data).encode() if data else b""
            response = await nc.request(subject, payload, timeout=2)
            return json.loads(response.data)
        finally:
            await nc.close()

    def spawn_child(self, payload: dict = None) -> dict:
        """
        Spawn a child agent via NATS.
        """
        agent_id = os.getenv("AGENT_ID")
        if not agent_id:
            raise ValueError("AGENT_ID environment variable not set")

        req_data = {"parent_id": agent_id, "payload": payload or {}}

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    self._make_request("evolution.spawn", req_data), loop
                ).result()
            else:
                result = asyncio.run(self._make_request("evolution.spawn", req_data))
        except RuntimeError:
            result = asyncio.run(self._make_request("evolution.spawn", req_data))

        logger.info(f"Agent spawned: {result}")
        return result


# Structured Logging Configuration with component tagging
logger.add("system.log", format="{time} {level} [component:agent-genesis] {message}", level="DEBUG", rotation="10 MB")

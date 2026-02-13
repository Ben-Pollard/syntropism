import asyncio
import json

import nats
from loguru import logger


class MCPGateway:
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.js = None

    async def connect(self):
        self.nc = await nats.connect(self.nats_url)
        self.js = self.nc.jetstream()
        logger.info(f"MCPGateway connected to NATS at {self.nats_url}")

    async def setup_stream(self):
        # Create stream for MCP requests
        await self.js.add_stream(name="mcp_requests", subjects=["mcp.request.*"])
        logger.info("MCPGateway setup stream 'mcp_requests'")

    async def run(self):
        # Pull consumer
        sub = await self.js.pull_subscribe("mcp.request.*", "mcp_gateway_consumer")

        logger.info("MCPGateway started pulling requests...")
        while True:
            try:
                msgs = await sub.fetch(1, timeout=1)
                for msg in msgs:
                    data = json.loads(msg.data)
                    logger.info(f"MCPGateway received request: {data}")
                    # Here we would forward to MCP server
                    # For now, just ack
                    await msg.ack()
            except nats.errors.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"MCPGateway error: {e}")
                await asyncio.sleep(1)

    async def close(self):
        if self.nc:
            await self.nc.close()

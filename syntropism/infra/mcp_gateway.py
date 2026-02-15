import asyncio
import json

import nats
from loguru import logger

from syntropism.core.observability import extract_context, setup_tracing

# Initialize OTEL
tracer = setup_tracing("mcp-gateway")


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

    async def run(self, max_msgs: int | None = None):
        # Pull consumer
        sub = await self.js.pull_subscribe("mcp.request.*", "mcp_gateway_consumer")

        logger.info("MCPGateway started pulling requests...")
        msgs_processed = 0
        while True:
            if max_msgs is not None and msgs_processed >= max_msgs:
                break
            try:
                msgs = await sub.fetch(1, timeout=1)
                for msg in msgs:
                    context = extract_context(msg.headers)
                    with tracer.start_as_current_span("mcp_request_handler", context=context) as span:
                        data = json.loads(msg.data)
                        logger.info(f"MCPGateway received request: {data}")

                        # OpenInference Tool Instrumentation
                        span.set_attribute("openinference.span.kind", "TOOL")
                        span.set_attribute("tool.name", data.get("tool", "unknown"))
                        span.set_attribute("tool.parameters", json.dumps(data.get("parameters", {})))

                        # Here we would forward to MCP server
                        # For now, just ack
                        await msg.ack()
                        msgs_processed += 1
            except nats.errors.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"MCPGateway error: {e}")
                await asyncio.sleep(1)

    async def close(self):
        if self.nc:
            await self.nc.close()

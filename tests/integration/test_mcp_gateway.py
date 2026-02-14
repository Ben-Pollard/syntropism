import asyncio
import json

import nats
import pytest

from syntropism.infra.mcp_gateway import MCPGateway


@pytest.mark.asyncio
async def test_mcp_gateway_pull():
    gateway = MCPGateway()
    await gateway.connect()
    await gateway.setup_stream()

    # Start gateway in background
    task = asyncio.create_task(gateway.run())

    # Client publishing request
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    payload = {"method": "list_tools", "params": {}}
    await js.publish("mcp.request.test", json.dumps(payload).encode())

    await asyncio.sleep(2)  # Wait for gateway to process

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await nc.close()
    await gateway.close()

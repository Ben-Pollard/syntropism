import asyncio
import json

import nats
import pytest

from syntropism.benchmarks.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_benchmark_runner_fc1():
    runner = BenchmarkRunner()
    await runner.connect()
    await runner.start_collecting()

    # Mock agent emitting events for FC-1
    nc = await nats.connect("nats://localhost:4222")
    events = [
        {"type": "tool_call_initiated", "tool_name": "economic.get_balance"},
        {"type": "balance_queried"},
        {"type": "tool_call_initiated", "tool_name": "market.bid"},
        {"type": "bid_placed", "total_cost": 450}
    ]

    for event in events:
        await nc.publish("benchmark_events", json.dumps(event).encode())

    await asyncio.sleep(0.5) # Wait for collection

    scenario = {
        "task_id": "fc_001",
        "validation": {
            "required_event_sequence": [
                {"type": "tool_call_initiated", "tool_name": "economic.get_balance"},
                {"type": "balance_queried"},
                {"type": "tool_call_initiated", "tool_name": "market.bid"},
                {"type": "bid_placed"}
            ],
            "forbidden_events": [
                {"type": "bid_rejected"}
            ]
        }
    }

    assert runner.validate_scenario(scenario) is True

    await nc.close()
    await runner.close()

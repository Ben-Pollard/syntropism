import json

import nats
from loguru import logger


class BenchmarkRunner:
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.events = []

    async def connect(self):
        self.nc = await nats.connect(self.nats_url)
        logger.info(f"BenchmarkRunner connected to NATS at {self.nats_url}")

    async def start_collecting(self):
        async def event_handler(msg):
            event = json.loads(msg.data)
            self.events.append(event)
            logger.debug(f"BenchmarkRunner collected event: {event}")

        await self.nc.subscribe("system.*.*", cb=event_handler)

    def validate_scenario(self, scenario: dict) -> bool:
        required_sequence = scenario.get("validation", {}).get("required_event_sequence", [])
        forbidden_events = scenario.get("validation", {}).get("forbidden_events", [])

        # Check for forbidden events
        for event in self.events:
            for forbidden in forbidden_events:
                if all(event.get(k) == v for k, v in forbidden.items()):
                    logger.error(f"Forbidden event detected: {event}")
                    return False

        # Check for required sequence (order matters)
        event_idx = 0
        for required in required_sequence:
            found = False
            while event_idx < len(self.events):
                event = self.events[event_idx]
                event_idx += 1
                # Match required event (simple equality for now)
                # Handle constraints if present
                match = True
                for k, v in required.items():
                    if k == "constraints":
                        continue # TODO: Implement constraint validation
                    if event.get(k) != v:
                        match = False
                        break

                if match:
                    found = True
                    break

            if not found:
                logger.error(f"Required event not found in sequence: {required}")
                return False

        return True

    async def close(self):
        if self.nc:
            await self.nc.close()

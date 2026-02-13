# NATS & Observability Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Migrate the system from a REST-based architecture to a NATS-based event-driven architecture with full observability and benchmark support.

**Architecture:** The system will use NATS JetStream for durable message streams and request-reply patterns. OpenTelemetry (OTEL) will be used for distributed tracing, with traces propagated through NATS headers. A new Benchmark Runner will validate system behavior against event sequences.

**Tech Stack:** NATS, JetStream, OpenTelemetry, Python (nats-py, opentelemetry-sdk), Docker, FastAPI (legacy support).

---

### Task 1: Infrastructure Setup (NATS & OTEL)

**Files:**
- Create: `docker-compose.nats.yml`
- Create: `otel-collector-config.yaml`

**Step 1: Create NATS and OTEL infrastructure**
Create `docker-compose.nats.yml` with NATS (JetStream enabled) and OTEL Collector.

```yaml
version: '3.8'
services:
  nats:
    image: nats:latest
    command: "-js -sd /data"
    ports:
      - "4222:4222"
      - "8222:8222"
    volumes:
      - nats_data:/data

  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"

volumes:
  nats_data:
```

**Step 2: Configure OTEL Collector**
Create `otel-collector-config.yaml`.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  logging:
    verbosity: normal

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
```

**Step 3: Verify infrastructure**
Run: `docker-compose -f docker-compose.nats.yml up -d`
Expected: NATS and OTEL collector containers are running.

---

### Task 2: Service Layer Refactoring (TDD)

**Files:**
- Modify: `syntropism/economy.py`
- Modify: `syntropism/market.py`
- Modify: `syntropism/service.py`
- Test: `tests/integration/test_nats_services.py`

**Step 1: Write failing test for NATS Economic Service**
Create `tests/integration/test_nats_services.py`.

```python
import pytest
import asyncio
import nats
from syntropism.contracts import BidRequest

@pytest.mark.asyncio
async def test_economic_balance_nats():
    nc = await nats.connect("nats://localhost:4222")
    # This should fail until the handler is implemented
    response = await nc.request("economic.balance.agent_1", b"")
    assert response.data == b'{"agent_id": "agent_1", "balance": 1000.0}'
    await nc.close()
```

**Step 2: Implement NATS handler in `syntropism/economy.py`**
Add NATS connection and handler logic to `EconomicEngine`.

**Step 3: Run test and verify pass**
Run: `pytest tests/integration/test_nats_services.py`

**Step 4: Repeat for Market and Social services**

---

### Task 3: Agent Runtime Update

**Files:**
- Modify: `workspaces/genesis/services.py`
- Modify: `runtime/Dockerfile`
- Modify: `runtime/pyproject.toml`

**Step 1: Update Agent dependencies**
Add `nats-py` and `opentelemetry-sdk` to `runtime/pyproject.toml`.

**Step 2: Refactor `EconomicService` to use NATS**
Modify `workspaces/genesis/services.py` to use `nats-py` instead of `httpx`.

```python
class EconomicService:
    def __init__(self, nats_url: str = "nats://nats:4222"):
        self.nats_url = nats_url

    async def get_balance(self, agent_id: str) -> dict:
        nc = await nats.connect(self.nats_url)
        res = await nc.request(f"economic.balance.{agent_id}", b"")
        await nc.close()
        return json.loads(res.data)
```

---

### Task 4: Benchmark Runner Implementation

**Files:**
- Create: `syntropism/benchmarks/runner.py`
- Test: `tests/integration/test_benchmark_runner.py`

**Step 1: Implement Event Sequence Validator**
Create `syntropism/benchmarks/runner.py` that consumes from `benchmark_events` stream and validates against `11_benchmark_scenarios.md`.

**Step 2: Verify with Scenario FC-1**
Run a mock agent that emits the required events and verify the runner marks it as success.

---

### Task 5: MCP Gateway Implementation

**Files:**
- Create: `syntropism/mcp_gateway.py`

**Step 1: Implement NATS Pull Consumer**
Create a gateway that pulls from `mcp_requests` and forwards to external APIs.

---

### Task 6: Verification & Observability Checkpoints

**Step 1: Verify Trace Propagation**
Ensure `trace_id` is present in NATS headers and visible in OTEL collector logs.

**Step 2: Final E2E Test**
Run `tests/e2e/test_scenarios.py` (updated for NATS) and verify all benchmarks pass.

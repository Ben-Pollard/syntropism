# Observability & OpenInference Standardization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Consolidate observability infrastructure, implement distributed trace continuity across NATS, and standardize LLM/Tool instrumentation using OpenInference semantic conventions for Arize Phoenix compatibility.

**Architecture:** 
- **Infrastructure**: Unified `docker-compose.yml` with OTel Collector (optimized with processors) and Arize Phoenix.
- **Trace Continuity**: W3C Trace Context propagation via NATS headers using `opentelemetry.propagate`.
- **Instrumentation**: Manual instrumentation of `LLMProxy` and `MCPGateway` using OpenInference semantic attributes (e.g., `llm.model_name`, `openinference.span.kind`).

**Tech Stack:**
- OpenTelemetry SDK (Python)
- OpenInference Semantic Conventions
- NATS JetStream
- Arize Phoenix
- Docker Compose

---

### Task 1: Infrastructure Consolidation

**Files:**
- Create: `docker-compose.yml` (renamed from `docker-compose.nats.yml`)
- Modify: `otel-collector-config.yaml`
- Delete: `docker-compose.nats.yml`

**Step 1: Rename and update Docker Compose**
```bash
mv docker-compose.nats.yml docker-compose.yml
```

**Step 2: Update `docker-compose.yml`**
Ensure `phoenix` and `otel-collector` are correctly configured.
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
    depends_on:
      - phoenix

  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
    environment:
      - PHOENIX_PORT=6006
      - PHOENIX_HOST=0.0.0.0

volumes:
  nats_data:
```

**Step 3: Update `otel-collector-config.yaml` with processors**
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 512
  memory_limiter:
    check_interval: 5s
    limit_percentage: 80
    spike_limit_percentage: 25

exporters:
  debug:
    verbosity: normal
  otlp/phoenix:
    endpoint: phoenix:6006
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug, otlp/phoenix]
```

**Step 4: Verify infrastructure**
Run: `docker compose up -d`
Expected: All services start, Phoenix accessible at `http://localhost:6006`.

---

### Task 2: NATS Trace Context Propagation

**Files:**
- Modify: `syntropism/domain/economy.py`
- Modify: `syntropism/core/genesis.py`
- Modify: `syntropism/infra/mcp_gateway.py`

**Step 1: Implement Propagation Utility**
Add helper functions for injecting/extracting context from NATS headers.

**Step 2: Update `EconomicEngine.run_nats`**
Extract context in `balance_handler`.
```python
from opentelemetry import propagate

async def balance_handler(msg):
    context = propagate.extract(msg.headers or {})
    with tracer.start_as_current_span("balance_handler", context=context) as span:
        # ... existing logic
```

**Step 3: Update `EvolutionManager.run_nats`**
Extract context in `spawn_handler`.
```python
async def spawn_handler(msg):
    context = propagate.extract(msg.headers or {})
    with tracer.start_as_current_span("spawn_handler", context=context) as span:
        # ... existing logic
```

**Step 4: Update NATS Publishers**
Inject context when publishing/requesting.
```python
headers = {}
propagate.inject(headers)
await nc.publish(subject, data, headers=headers)
```

---

### Task 3: OpenInference LLM Instrumentation

**Files:**
- Modify: `syntropism/infra/llm_proxy.py`

**Step 1: Add OpenInference attributes to `handle_llm_request`**
```python
from opentelemetry import trace

@router.post("/llm")
async def handle_llm_request(request: LLMRequest, req: Request):
    with tracer.start_as_current_span("llm_request") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("llm.model_name", request.model)
        span.set_attribute("llm.input_messages.0.message.role", "user")
        span.set_attribute("llm.input_messages.0.message.content", request.prompt)
        
        # ... call LLM ...
        
        span.set_attribute("llm.output_messages.0.message.role", "assistant")
        span.set_attribute("llm.output_messages.0.message.content", response_text)
        span.set_attribute("llm.token_count.total", requested_tokens)
```

---

### Task 4: OpenInference Tool & Task Instrumentation

**Files:**
- Modify: `syntropism/infra/mcp_gateway.py`
- Modify: Agent loop (wherever it resides, likely `syntropism/core/orchestrator.py`)

**Step 1: Instrument MCP Tool Calls**
In `MCPGateway.run`, wrap tool execution in a span.
```python
with tracer.start_as_current_span("mcp_tool_call") as span:
    span.set_attribute("openinference.span.kind", "TOOL")
    span.set_attribute("tool.name", tool_name)
    span.set_attribute("tool.parameters", json.dumps(parameters))
```

**Step 2: Instrument Agent Reasoning Loop**
In `Orchestrator`, wrap the main loop in an `AGENT` or `CHAIN` span.
```python
with tracer.start_as_current_span("agent_loop") as span:
    span.set_attribute("openinference.span.kind", "AGENT")
    # ...
```

---

### Task 5: Verification

**Step 1: Run a benchmark scenario**
Run: `poetry run python -m syntropism.cli benchmark run --scenario er_001`

**Step 2: Check Arize Phoenix**
- Verify trace continuity: A single trace should span from the initial request to the LLM call and tool execution.
- Verify OpenInference attributes: LLM spans should have the "LLM" icon and show prompt/response correctly.
- Verify Tool spans: Tool calls should show name and parameters.

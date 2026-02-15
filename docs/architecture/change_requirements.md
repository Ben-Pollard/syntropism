# Change Requirements: Observability & Behavioral Tracing

This document outlines the technical requirements for implementing the agreed observability stack, focusing on Arize Phoenix, OpenTelemetry (OTel), and NATS JetStream.

## 1. Infrastructure Consolidation

### 1.1 Unified Docker Compose
- **Requirement**: Consolidate all infrastructure dependencies into a single `docker-compose.yml` file.
- **Implementation**:
    - Rename `docker-compose.nats.yml` to `docker-compose.yml`.
    - Ensure `nats`, `otel-collector`, and `phoenix` services are present.
    - Configure `phoenix` to use port `6006`.
    - Configure `otel-collector` to depend on `phoenix`.
- **Verification**: `docker compose up -d` starts all three services without errors.

### 1.2 OTel Collector Optimization
- **Requirement**: Configure the OTel Collector for production-like reliability and Phoenix compatibility.
- **Implementation**:
    - Update `otel-collector-config.yaml`.
    - Add `memory_limiter` processor to prevent OOM (limit: 80%, spike: 25%, check_interval: 5s).
    - Add `batch` processor to optimize export (timeout: 10s, send_batch_size: 512).
    - Ensure `otlp/phoenix` exporter points to `phoenix:6006` with `insecure: true`.
- **Verification**: Collector logs show successful connection to Phoenix and no processor drops.

## 2. Distributed Trace Continuity

### 2.1 NATS Header Propagation
- **Requirement**: Implement W3C Trace Context propagation across all NATS-based service communication.
- **Implementation**:
    - **Inject**: In NATS publishers (e.g., `nc.request`, `nc.publish`), inject the current span context into NATS headers using the `W3CTraceContextPropagator`.
    - **Extract**: In NATS subscribers (e.g., `balance_handler`, `spawn_handler`), extract the context from `msg.headers` before starting a new span.
    - **Fallback**: If no header is present, start a new root span.
- **Modified Files**:
    - `syntropism/domain/economy.py`
    - `syntropism/core/genesis.py`
    - `syntropism/infra/mcp_gateway.py`
- **Verification**: A single trace ID is shared between a requester and a responder in Arize Phoenix.

## 3. OpenInference Standardization

### 3.1 LLM Instrumentation
- **Requirement**: Standardize LLM request/response tracing using OpenInference semantic conventions.
- **Implementation**:
    - Update `syntropism/infra/llm_proxy.py`.
    - Wrap LLM calls in a span with `span_kind="LLM"`.
    - Set OpenInference attributes:
        - `llm.model_name`
        - `llm.prompts.0.content`
        - `llm.output_messages.0.content`
        - `llm.token_count.total`
- **Verification**: Arize Phoenix displays the LLM call with the "LLM" icon and correctly parses prompt/response.

### 3.2 Tool & Task Instrumentation
- **Requirement**: Instrument tool calls and agent tasks using OpenInference conventions.
- **Implementation**:
    - Update `syntropism/infra/mcp_gateway.py` and agent loop.
    - Use `span_kind="TOOL"` for MCP tool invocations.
    - Use `span_kind="CHAIN"` or `span_kind="AGENT"` for high-level agent reasoning loops.
    - Set `tool.name` and `tool.parameters` attributes.
- **Verification**: Trace visualization shows a clear hierarchy of Agent -> Chain -> LLM/Tool.

## 4. Verification Criteria

### 4.1 Trace Completeness
- **Test**: Trigger an agent spawn request via NATS.
- **Success**: A single trace in Phoenix shows:
    1. `evolution.spawn` (NATS Request)
    2. `spawn_handler` (NATS Subscriber)
    3. `_create_agent_with_workspace` (Internal Function)
    4. Database operations (SQLAlchemy spans)

### 4.2 OpenInference Compliance
- **Test**: Execute a benchmark scenario that involves LLM calls.
- **Success**: Phoenix "Attributes" tab for the LLM span contains all required `llm.*` fields, and the "Evaluation" tab is ready for Phoenix Evals.

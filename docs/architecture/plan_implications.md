# Architectural Implications: Observability & NATS Migration

This document analyzes the technical debt, breaking changes, and infrastructure requirements introduced by the transition to an OpenInference-based observability stack and NATS-based event-driven architecture.

## 1. Executive Summary
The shift from REST/SQLite-centric operations to a distributed, event-driven system using NATS and Arize Phoenix introduces significant architectural rigor. While it solves visibility gaps in agent reasoning, it requires a fundamental change in how services communicate, how state is managed, and how benchmarks are validated.

## 2. Breaking Changes

### 2.1 Communication Protocol
- **REST to NATS**: All inter-service communication is moving to NATS. The legacy FastAPI endpoints in `syntropism/api/service.py` are being deprecated in favor of NATS request-reply and JetStream work queues.
- **Synchronous to Asynchronous**: Operations that were previously blocking (e.g., `get_balance`) now require timeout handling and asynchronous message patterns.

### 2.2 Resource Allocation Model
- **Unit-based to Capacity-based**: Transitioning from absolute units (e.g., `cpu_seconds=2.0`) to capacity percentages (e.g., `cpu_percent=0.1`) over a duration. This breaks existing `ResourceBundle` and `Bid` models.
- **Auction-based Pricing**: Formulaic price adjustments are being replaced by emergent "Price Discovery" from winning bids.

### 2.3 Event Taxonomy
- **Schema Standardization**: Transitioning from ad-hoc logging to a strict Pydantic-validated event taxonomy (`SystemEvent`, `AgentEvent`, `JudgeEvent`).
- **Benchmark Data**: Existing benchmark JSON files (e.g., `er_001.json`) are incompatible with the new event-driven validation logic and must be rewritten.

## 3. Technical Debt

### 3.1 Legacy API Support
- **Dual-Stack Maintenance**: During the migration, the system must support both REST (for legacy agents/tests) and NATS. This creates temporary complexity in the service layer.
- **SQLite vs. KV Store**: The system currently relies on SQLite for state. The NATS migration introduces JetStream KV stores, leading to potential state duplication or drift if not carefully managed.

### 3.2 Instrumentation Gaps
- **Manual OTel Spans**: Current instrumentation in `EconomicEngine` is manual. This needs to be replaced or augmented with `openinference-instrumentation` to capture LLM-specific semantic conventions.
- **NATS Header Propagation**: Standard NATS clients do not propagate W3C Trace Context. Custom wrappers for `nc.publish` and `nc.subscribe` are required to prevent trace fragmentation.

### 3.3 Benchmark Runner
- **Event Sequence Validation**: The `BenchmarkRunner` currently lacks full integration with the new event taxonomy. It needs a complete overhaul to support JetStream-based event sourcing and correlation-id-based filtering.

## 4. New Infrastructure Requirements

### 4.1 Observability Stack
- **Arize Phoenix**: Required for trace visualization and embedding analysis.
- **OTel Collector**: Required to aggregate spans and route them to Phoenix. Must be configured with `tail_sampling` to manage high span volume from agent loops.
- **OpenInference SDKs**: New dependencies for all agent-facing services.

### 4.2 NATS JetStream
- **Durable Streams**: Required for `audit_log` and `mcp_requests`.
- **KV Buckets**: Required for `agent_state` and `market_prices`.
- **Cluster Topology**: Transitioning from single-node NATS to a 3-node cluster for production resilience.

## 5. Implementation Roadmap (High-Level)

1.  **Infrastructure**: Deploy NATS, OTel Collector, and Arize Phoenix via Docker Compose.
2.  **Service Refactoring**: Implement NATS handlers and OTel instrumentation in core services (Economy, Market, Scheduler).
3.  **Agent Runtime**: Update agent service layer to use `nats-py` and inject trace context.
4.  **Benchmark Overhaul**: Populate benchmark data with new taxonomy and update the runner to validate against JetStream events.
5.  **Cleanup**: Decommission REST endpoints and legacy logging.

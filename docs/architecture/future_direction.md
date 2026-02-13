# Future Architectural Direction: Developer Experience & Observability

This document outlines the agreed architectural direction for the next phase of the `bp-agents-2` project, prioritizing developer experience (DX) and observability while maintaining the system's "laptop-bound" simplicity.

## 1. Core Objectives

1.  **Prioritize Developer Experience (DX)**: Maintain the synchronous orchestration loop and bind-mounted workspaces for easy debugging and state inspection.
2.  **Unified Communication Strategy**: Resolve the "two ways of communicating" smell by deciding on the role of NATS vs. REST for external integrations.
3.  **Benchmark-Driven Development**: Integrate the `BenchmarkRunner` into the test suite to provide immediate feedback on agent performance.
4.  **Observability-First**: Leverage the newly implemented NATS/OTEL stack for deep tracing of agent reasoning and system interactions.

## 2. Key Decisions

### Decision 1: Retain Synchronous Orchestration & Bind Mounts
-   **Direction**: Keep the `Orchestrator` as a synchronous loop and workspaces as host-bound bind mounts.
-   **Rationale**: Scaling is not currently a bottleneck. Bind mounts and synchronous execution are critical for `debugpy` support and direct filesystem inspection. Distributed persistence is deferred (YAGNI).

### Decision 2: Hybrid Communication (NATS for Internal, REST for External)
-   **Direction**: Use NATS for all *internal* agent-to-system interactions (Economy, Market, Social). Use REST/FastAPI for *external* gateways (LLM APIs, MCP, third-party integrations).
-   **Rationale**: Avoids the overhead of writing NATS translations for every open-source AI/ML project. The FastAPI service acts as a "Cognitive Gateway" that bridges external REST/gRPC APIs to the internal NATS-based agent environment.

### Decision 3: Test-Integrated Benchmarking
-   **Direction**: The `BenchmarkRunner` will initially be used as a validation tool within the integration test suite.
-   **Implementation**: Tests will launch agents, collect NATS events, and use the `BenchmarkRunner` to verify `required_event_sequence` and `forbidden_events`.

### Decision 4: Observability as the "Source of Truth"
-   **Direction**: Use OTEL traces and NATS event logs as the primary means of auditing agent behavior, rather than just `system.log`.
-   **Implementation**: Ensure all internal service handlers (Economic, Market) are fully instrumented with OTEL spans that propagate through NATS headers.

## 3. Success Criteria

-   **Zero-Config Debugging**: Developers can still attach VS Code to a running agent container via `debugpy` without complex network setup.
-   **Transparent Benchmarking**: Running `pytest` provides a clear pass/fail report based on the benchmark scenarios in `docs/design/11_benchmark_scenarios.md`.
-   **Clean Gateway Boundaries**: A clear distinction between internal NATS subjects and external REST/MCP endpoints.
-   **Trace Visibility**: Every agent request can be traced from the agent's `EconomicService` through NATS to the `EconomicEngine` and back.

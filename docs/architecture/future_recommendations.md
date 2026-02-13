# Architectural Recommendations: bp-agents-2

This document provides recommendations for the evolution of the `bp-agents-2` system, prioritizing developer experience and observability while maintaining the system's "laptop-bound" simplicity.

## 1. Scalability & Performance

### Current State
The system uses NATS for internal communication, enabling event-driven patterns. The `Orchestrator` remains a synchronous loop, which is appropriate for the current "laptop-bound" phase.

### Recommendations
- **NATS for Internal Events**: Continue using NATS for all internal agent-system interactions to support benchmarking and tracing.
- **Keep Synchronous Orchestration**: Maintain the current sequential execution loop to preserve easy debugging and predictable resource allocation on a single machine.
- **SQLite for Persistence**: Continue using SQLite; it is sufficient for current loads and simplifies the developer setup.

## 2. Security & Isolation

### Current State
Agents run in Docker containers with bind-mounted workspaces. Communication is via NATS.

### Recommendations
- **Workspace Sanitization**: Implement stricter validation on workspace paths in `WorkspaceService` to prevent path traversal, even with bind mounts.
- **NATS Subject Namespacing**: Use structured subject namespacing (e.g., `agent.<id>.economic.balance`) to prepare for future isolation, even if full NATS accounts are not yet implemented.
- **Read-Only Root FS**: Run agent containers with a read-only root filesystem to prevent persistent changes outside the `/workspace` volume.

## 3. Resilience & Observability

### Current State
The system uses NATS and OTEL. NATS handlers are hosted within the FastAPI process.

### Recommendations
- **OTEL for Reasoning Traces**: Use OpenTelemetry to trace not just system calls, but also internal agent reasoning steps (e.g., LLM prompts/responses) to provide a complete audit trail.
- **NATS Event Logging**: Use NATS as a real-time event log for the `BenchmarkRunner`, allowing for live monitoring of agent progress during tests.
- **Graceful Shutdown**: Ensure NATS connections and OTEL exporters are gracefully closed during system shutdown to prevent data loss in traces.

## 4. Maintainability & DX

### Current State
The system is in a hybrid state with both FastAPI REST and NATS.

### Recommendations
- **Cognitive Gateway Pattern**: Formalize the FastAPI service as a "Cognitive Gateway". It should handle external REST/MCP integrations and translate them into NATS events for the agents.
- **Internal NATS Standardization**: Standardize all *internal* system services (Economy, Market, Social) on NATS to eliminate the "two ways of communicating" smell for core logic.
- **Test-Integrated Benchmarks**: Integrate the `BenchmarkRunner` directly into `pytest` to ensure that every architectural change is validated against the benchmark scenarios.
- **Unified Logging/Tracing**: Consolidate `system.log` and OTEL traces so that log messages include `trace_id` for easy cross-referencing in developer tools.

## Summary of Alignment

| Standard | Status | Key Gap |
| :--- | :--- | :--- |
| **SOLID** | Improved | NATS handlers decouple service logic from HTTP concerns. |
| **Clean Architecture** | Improved | Clearer boundary between internal (NATS) and external (REST) communication. |
| **Twelve-Factor App** | Partial | Local filesystem dependency (bind mounts) is a conscious choice for DX. |
| **Agent Patterns** | Strong | Excellent observability and benchmarking support. |

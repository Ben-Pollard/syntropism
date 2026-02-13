# Architectural Plan Implications: Benchmarks & Cognitive Gateway

This document identifies the technical debt, breaking changes, and infrastructure requirements introduced by the upcoming plans for benchmarking and the formalization of the Cognitive Gateway.

## 1. Audit of `docs/design/11_benchmark_scenarios.md` (Test Integration)

### Technical Debt
- **Event Consistency**: To support reliable benchmarking in tests, every system service must consistently publish events to the `benchmark_events` subject.
- **Mocking NATS in Tests**: Integration tests now require a running NATS server, increasing the complexity of the test environment.

### Breaking Changes
- **Test Runner**: Existing E2E tests must be refactored to use the `BenchmarkRunner` for validation instead of direct database or API checks.

### New Infrastructure Requirements
- **NATS for CI**: CI/CD pipelines must now include a NATS sidecar for integration testing.

## 2. Audit of "Cognitive Gateway" (REST vs. NATS)

### Technical Debt
- **Translation Layer**: Formalizing the "Cognitive Gateway" requires building and maintaining a translation layer between external REST/MCP APIs and internal NATS subjects.
- **Protocol Mismatch**: Handling the impedance mismatch between synchronous REST calls and asynchronous NATS messaging (e.g., timeouts, error propagation).

### Breaking Changes
- **Service Deprecation**: Internal services that still rely on REST (e.g., `spawn`, `transfer`) must be migrated to NATS to maintain the "Internal NATS" standard.

### New Infrastructure Requirements
- **MCP Gateway**: A dedicated component within the FastAPI service to bridge NATS requests to external MCP servers.

## 3. Summary of Risks

1.  **Developer Friction**: If the NATS/REST translation layer is complex, it may slow down the integration of new AI/ML tools.
2.  **Test Flakiness**: Asynchronous event-based testing is inherently more prone to flakiness than synchronous API testing.
3.  **Complexity**: Maintaining two communication protocols (NATS for internal, REST for external) requires clear boundaries and documentation to avoid confusion.

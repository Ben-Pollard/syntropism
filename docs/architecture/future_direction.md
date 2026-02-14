# Future Architectural Direction: Market Alignment & Event-Driven Benchmarking

This document formalizes the agreed architectural direction for aligning the system's market dynamics and event emission with the benchmark requirements.

## 1. Core Principles

1.  **Market-Driven Price Discovery**: Prices are not set by a central authority but emerge from the interaction of system capacity and agent needs. The `MarketManager` facilitates discovery rather than dictating price.
2.  **Physics of Scarcity**: Resources (CPU, Memory, Tokens, Attention) are finite, strictly enforced, and priced per unit time.
3.  **Event-Driven Truth**: The system's state changes are communicated via an immutable, structured event stream. This stream is the "Source of Truth" for the `BenchmarkRunner`.
4.  **System-First Event Design**: Event structures are derived from best practices and existing system services. The benchmark definitions must align with these system-emitted events, not vice versa.

## 2. Key Decisions

### Decision 1: Refine Resource Allocation to Time-Based Bundles
-   **Direction**: Transition from "one-off" resource purchases to time-based "Resource Bundles" (e.g., 10% CPU for 10 minutes).
-   **Rationale**: Aligns with `docs/design/03_market.md`. Prevents "Partial Existence" and ensures agents have a predictable execution window.

### Decision 2: Implement System-Wide LLM Spend Limits
-   **Direction**: Define a maximum spend per unit time for upstream LLM services.
-   **Rationale**: Places commercial LLM usage into the same "Physical Scarcity" space as CPU and Memory.

### Decision 3: Standardize Event Taxonomy based on System Services
-   **Direction**: Define a unified event schema and taxonomy (e.g., `bid_placed`, `resources_allocated`, `credits_transferred`) based on the actual capabilities of the `EconomicEngine`, `MarketManager`, and `Scheduler`.
-   **Rationale**: Ensures the benchmark reflects the actual system dynamics. Identifies gaps where the benchmark requires events the system cannot yet emit.

### Decision 4: NATS-First Event Emission
-   **Direction**: All core domain services (Economy, Market, Scheduler) must emit events to NATS as their primary means of notifying the system of state changes.
-   **Rationale**: Decouples the `BenchmarkRunner` and other observability tools from the internal implementation details of the services.

## 3. Success Criteria

-   **Dynamic Pricing**: Market prices fluctuate based on actual utilization and agent bidding behavior.
-   **Hard Enforcement**: Agents are terminated or denied service if they exceed their allocated time-based bundle.
-   **Benchmark Alignment**: The `BenchmarkRunner` can successfully validate agent behavior using the standardized system event stream.
-   **Traceable Economy**: Every credit transfer and resource allocation is visible as a discrete event in the NATS stream.

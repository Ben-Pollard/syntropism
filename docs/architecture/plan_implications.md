# Plan Implications: Technical Debt and Breaking Changes

## Technical Debt Identified

### 1. Event Emission Gap
The core domain logic (`EconomicEngine`, `MarketManager`, `AllocationScheduler`) is currently decoupled from the event bus. Implementing the event taxonomy from `docs/design/10_agent_benchmark.md` requires injecting NATS publishing capabilities into these classes, which currently rely on static methods or direct DB access.

### 2. Hardcoded Pricing Logic
The `MarketManager` uses hardcoded factors (`PRICE_INCREASE_FACTOR`, `PRICE_DECREASE_FACTOR`) and thresholds. This makes it difficult to simulate different economic conditions (e.g., hyperinflation, resource abundance) without code changes.

## Breaking Changes Required

### 1. NATS Subject Hierarchy
To support the `BenchmarkRunner` and future observability, the NATS subject structure needs to be standardized.
- **Current**: `market.state.*`, `market.bid`, `economic.balance.*`
- **Proposed**: `system.market.price_update`, `system.economy.credits_transferred`, `agent.<id>.bid_placed`, `agent.<id>.reasoning_trace`.
- **Impact**: Existing agents and tools using the old subjects will break.

### 2. Resource Bundle Schema
The `ResourceBundle` model and its usage in `AllocationScheduler` need to be strictly aligned with the event data structures. Adding new resource types or changing units (e.g., `cpu_seconds` to `millicores`) will require database migrations and updates to all bidding logic.



## Implementation Strategy
1. **Phase 1: Event Instrumentation**: Update `Economy`, `Market`, and `Scheduler` to emit events.
2. **Phase 2: Schema Standardization**: Define Pydantic models for all events and update NATS subjects.
4. **Phase 4: Pricing Refinement**: Implement the "Physics of Scarcity" logic in `MarketManager`.

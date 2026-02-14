# Change Requirements: Market & Benchmark Alignment

This document translates the agreed architectural direction into actionable technical requirements for aligning the market dynamics and benchmark system.

## 1. Event Instrumentation Requirements

### 1.1 Unified Event Schema
-   **Requirement**: All system events must conform to the base schema defined in `docs/design/10_agent_benchmark.md`.
-   **Implementation**: Create a Pydantic-based `Event` model in `syntropism/domain/models.py` or a new `syntropism/domain/events.py`.

### 1.2 Economic Events
-   **Requirement**: `EconomicEngine` must emit `credits_transferred` events for every transaction.
-   **Requirement**: `EconomicEngine` must emit `balance_queried` events (optional, for audit).
-   **Requirement**: Implement a "Burn" account or mechanism where credits spent on resources are explicitly removed from circulation and recorded.

### 1.3 Market & Scheduler Events
-   **Requirement**: `AllocationScheduler` must emit `bid_placed`, `bid_rejected`, and `resources_allocated` events.
-   **Requirement**: `MarketManager` must emit `price_update` events whenever prices change due to utilization shifts.

## 2. Resource Market Requirements

### 2.1 Time-Based Allocation
-   **Requirement**: Update `ResourceBundle` and `Bid` models to include a `duration_minutes` or `end_timestamp`.
-   **Requirement**: `AllocationScheduler` must calculate availability based on *current* utilization of the total system capacity over the requested duration.
-   **Requirement**: Implement "All-or-Nothing" bundle allocation logic.

### 2.2 Price Discovery Logic
-   **Requirement**: Refactor `MarketManager.update_prices` to reflect supply/demand dynamics. Price should be a function of `(Total_Capacity - Current_Utilization)` and the volume of active bids.
-   **Requirement**: Implement "Attention" as a first-class resource with a fixed supply of 1.0.

### 2.3 LLM Spend Limits
-   **Requirement**: Add a `max_llm_spend_per_minute` configuration to the system.
-   **Requirement**: The `MarketManager` must treat this spend limit as the "100% utilization" point for the `tokens` resource.

## 3. Benchmark System Requirements

### 3.1 Scenario Definition Alignment
-   **Requirement**: Populate `syntropism/benchmarks/data/` JSON files with `required_event_sequence` that matches the new system event taxonomy.
-   **Requirement**: Scenarios must include realistic `initial_state` (balances, prices) and `validation` rules (constraints on event data).

### 3.2 Runner Expansion
-   **Requirement**: Update `BenchmarkRunner` to handle complex event matching, including:
    -   Partial data matching (e.g., "amount > 100").
    -   Temporal constraints (e.g., "event B must occur within 5s of event A").
    -   Source verification (e.g., "must be from 'system'").

## 4. Verification Criteria

-   **Unit Tests**: All new event emission logic must be covered by unit tests verifying NATS message content.
-   **Integration Tests**: A "Market Cycle" test must demonstrate:
    1.  Agent places bid.
    2.  Scheduler allocates bundle.
    3.  Economy burns credits.
    4.  Market updates price.
    5.  All 4 events are captured by a NATS subscriber.
-   **Benchmark Pass**: The `BenchmarkRunner` must successfully pass a basic `economic_reasoning` scenario using the live event stream.

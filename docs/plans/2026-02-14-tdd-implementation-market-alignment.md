# TDD Implementation: Market Alignment & Price Discovery

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Align the market and resource definitions with the "Physics of Scarcity" and "Price Discovery" principles in `docs/design/03_market.md`.

**Core Principles:**
1.  **Capacity-Based Bidding**: Agents bid for a percentage of total system capacity over a specific duration.
2.  **Auction-Based Price Discovery**: Prices are not set by formulas but emerge from the bids. The "Market Price" is the rate of the winning bids.
3.  **System-First Events**: Events are defined by the system's natural state changes, and the benchmark adapts to them.

---

### Task 1: Redefine Resource & Market Models

**Files:**
- Modify: `syntropism/domain/models.py`
- Test: `tests/unit/test_models_market.py`

**Step 1: Write failing tests**
Verify that `ResourceBundle` supports capacity percentages and duration, and `MarketState` tracks supply/utilization correctly.

**Step 2: Implementation**
- Update `ResourceBundle` to use `cpu_percent`, `memory_percent`, `tokens_percent`, `attention_percent` (all 0.0-1.0) and `duration_seconds`.
- Update `MarketState` to reflect that `available_supply` is a capacity measure (usually 1.0).

---

### Task 2: Implement Auction-Based Allocation

**Files:**
- Modify: `syntropism/core/scheduler.py`
- Test: `tests/unit/test_scheduler_auction.py`

**Step 1: Write failing tests**
Verify that the scheduler:
1.  Calculates current utilization by summing active executions.
2.  Sorts bids by total credit value.
3.  Allocates bundles only if *all* requested capacity percentages are available.
4.  Rejects bids that exceed available capacity.

**Step 2: Implementation**
- Refactor `run_allocation_cycle` to use the new capacity-based logic.
- Implement "All-or-Nothing" allocation.
- Ensure `LLM_SPEND_LIMIT` is used as the 100% capacity for tokens.

---

### Task 3: Implement Price Discovery & Reporting

**Files:**
- Modify: `syntropism/domain/market.py`
- Modify: `syntropism/core/scheduler.py`
- Test: `tests/unit/test_price_discovery.py`

**Step 1: Write failing tests**
Verify that:
1.  The scheduler calculates the "Market Price" (Credits per 100%-capacity-second) for each resource based on winning bids.
2.  The `MarketManager` updates `MarketState.current_market_price` with these discovered values.
3.  The `MarketManager` emits a `price_update` event (system-defined).

**Step 2: Implementation**
- Add logic to `AllocationScheduler` to derive the market rate from winning bids.
- Update `MarketManager` to report these rates.
- **Note**: Remove the formulaic `PRICE_INCREASE_FACTOR` logic; prices now "emerge".

---

### Task 4: System-First Event Instrumentation

**Files:**
- Create: `syntropism/domain/events.py` (Defined by system needs)
- Modify: `syntropism/domain/economy.py`, `syntropism/domain/market.py`, `syntropism/core/scheduler.py`
- Test: `tests/integration/test_system_events.py`

**Step 1: Implementation**
- Define Pydantic models for events that naturally occur in the services:
    - `economy.credits_burned` (when resources are bought)
    - `market.bid_processed` (result of a bid)
    - `market.price_discovered` (new market rates)
    - `execution.started` / `execution.terminated`
- Instrument the services to emit these events to NATS using the standardized hierarchy: `system.<service>.<event>`.

---

### Task 5: Benchmark Alignment & Verification

**Files:**
- Modify: `syntropism/benchmarks/runner.py`
- Modify: `syntropism/benchmarks/data/economic_reasoning/er001.json`
- Test: `tests/integration/test_benchmark_alignment.py`

**Step 1: Implementation**
- Update `BenchmarkRunner` to listen for the new system-defined events.
- Update `er001.json` (and others) to use the new event taxonomy and capacity-based resource definitions.
- Verify that a full market cycle (Bid -> Allocate -> Burn -> Discover Price) passes the benchmark validation.

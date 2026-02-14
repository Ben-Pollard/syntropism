# Implementation Plan: Benchmark and Market Alignment

## Goal
Align the current implementation of the market, economy, and scheduler with the event-driven benchmark design and the "Physics of Scarcity" principles, focusing on time-based resource allocation and instrumentation.

## Phase 1: Event Schema & Instrumentation
- [ ] Define Pydantic models for all events in `docs/design/10_agent_benchmark.md`.
- [ ] Update `EconomicEngine.transfer_credits` to emit `credits_transferred` events.
- [ ] Update `AllocationScheduler.place_bid` to emit `bid_placed` events.
- [ ] Update `AllocationScheduler.run_allocation_cycle` to emit `resources_allocated` and `bid_rejected` events.
- [ ] Update `MarketManager.update_prices` to emit `price_update` events.

## Phase 2: Resource & Market Logic Refinement
- [ ] Refactor `ResourceBundle` and `AllocationScheduler` to use time-based allocation (e.g., % of max capacity for duration).
- [ ] Implement system-wide LLM spend limit to define 100% LLM utilization.
- [ ] Refactor `MarketManager` to support non-linear price curves based on supply/demand as per `docs/design/03_market.md`.
- [ ] Implement "Attention" resource pricing and allocation logic.

## Phase 3: Verification
- [ ] Create unit tests for time-based allocation logic in `AllocationScheduler`.
- [ ] Verify that `MarketManager` price updates are triggered by high utilization in the `Scheduler`.
- [ ] Verify event emission via NATS for core economic and market actions.

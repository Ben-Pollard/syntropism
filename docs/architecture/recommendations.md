# Architectural Recommendations

## Scalability
- **NATS JetStream for Event Persistence**: Transition from standard NATS pub/sub to JetStream. This ensures that benchmark events are not lost if the `BenchmarkRunner` is temporarily disconnected and allows for "replay" of scenarios.
- **Asynchronous Price Updates**: Move `MarketManager.update_prices` out of the request-response cycle and into a background worker or a scheduled NATS task to prevent blocking resource allocation.
- **Database Indexing**: Ensure `Transaction` and `Bid` tables have composite indexes on `(agent_id, timestamp)` to support fast history and audit queries as the number of agents grows.

## Security
- **Atomic Transactions**: Ensure all credit transfers and resource allocations use strict database transactions (ACID) to prevent double-spending or resource over-allocation. The current `AllocationScheduler` uses `session.commit()` but needs careful error handling to ensure atomicity across multiple resource types.
- **Agent Isolation**: Implement strict workspace isolation (already hinted at in `models.py`) to ensure agents cannot access each other's files or the system's internal state except through authorized NATS subjects.
- **Validation of Bids**: Implement server-side validation of bid amounts against current balances *before* entering the allocation cycle to reduce noise and potential DoS from invalid bids.

## Resilience
- **Circuit Breakers for LLM Proxy**: The `infra/llm_proxy.py` (referenced in file list) should implement circuit breakers to handle upstream provider failures without crashing the economic simulation.
- **Idempotent Event Emission**: Ensure that if a process restarts, it doesn't emit duplicate events for the same state change. Use `event_id` (UUID) as defined in `10_agent_benchmark.md` to deduplicate at the collector level.
- **Graceful Degradation**: If the `MarketManager` is unavailable, the `Scheduler` should fall back to last-known prices rather than failing allocation.

## Maintainability
- **Centralized Event Registry**: Create a shared library or schema definition (e.g., using Pydantic) for all events defined in `10_agent_benchmark.md`. This ensures consistency between the emitters (Scheduler, Economy) and the consumer (BenchmarkRunner).
- **Dependency Injection**: Refactor `MarketManager` and `EconomicEngine` to use dependency injection for the NATS client and Database session, making unit testing easier without requiring live infrastructure.
- **Unified Logging and Tracing**: Expand the OpenTelemetry implementation in `economy.py` to cover the `Scheduler` and `MarketManager`, providing a full trace of a single bid from placement to allocation.

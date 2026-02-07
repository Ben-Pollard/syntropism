# Alignment Audit: Monolith Specification Implementation
**Date**: 2026-02-07
**Status**: In Progress

## Identified Gaps

### 1. Resource Consumption Logic
- **Gap**: In [`bp_agents/scheduler.py`](bp_agents/scheduler.py:74), the `AllocationScheduler` increments `consumed_supply` by a fixed `1.0` for every allocated bundle, regardless of the actual requirements (CPU, Memory, Tokens) specified in the `ResourceBundle`.
- **Spec Alignment**: The specification implies that resource allocation should be based on the actual units requested, ensuring that the total consumed resources do not exceed the `available_supply`.

### 2. Attention Mechanism Duality
- **Gap**: There is a slight ambiguity between "Attention" as a market resource (checked in [`bp_agents/scheduler.py`](bp_agents/scheduler.py:51)) and the `AttentionManager` in [`bp_agents/attention.py`](bp_agents/attention.py), which handles human prompts via a separate bidding and escrow system.
- **Spec Alignment**: Section 3.3 of the spec describes attention as a scarce resource with a single slot, but it's unclear if this should be managed entirely by the `AttentionManager` or if it should also be part of the `ResourceBundle` all-or-nothing allocation.

### 3. Missing Message Bus Integration
- **Gap**: While the [`bp_agents/models.py`](bp_agents/models.py:115) includes a `Message` model, there is no corresponding `MessageBus` implementation or API endpoint in [`bp_agents/service.py`](bp_agents/service.py) to facilitate agent-to-agent communication.
- **Spec Alignment**: Section 3.5 and 4.2 of the spec require a `MessageBus` for asynchronous coordination between agents.

### 4. Market Visibility
- **Gap**: The `MarketState` model and `MarketManager` do not yet expose the list of active bids or recent transactions to agents.
- **Spec Alignment**: Section 3.2 emphasizes "Market visibility" where all active bids and recent transactions are transparent to all agents to allow for strategy development.

### 5. System Initialization and Orchestration
- **Gap**: The system startup sequence described in Section 4.3 (loading config, initializing markets, creating genesis agent, starting the scheduler) is not yet visible in a central entry point.

## Socratic Inquiries

1. The `AllocationScheduler` currently treats every resource bundle as consuming "1 unit" of supply. Should we move to a unit-based consumption model (e.g., actual CPU seconds and MB of memory) to better reflect the "Economic Alignment" principle?
2. Should "Attention" be treated as a standard resource in the `ResourceBundle` (all-or-nothing allocation), or should it remain a separate high-priority bidding process managed by the `AttentionManager`?
3. For the `MessageBus`, should we implement a simple database-backed inbox as a first step, or move directly to an off-the-shelf solution like Redis as suggested in the spec?
4. How should we expose "Market Visibility" (active bids and transaction history) to agents while maintaining performance as the number of agents grows?

## Clarified Vision
*To be populated after user response*

## Action Items
- [ ] Refactor `AllocationScheduler` to use actual resource requirements for supply consumption.
- [ ] Implement `MessageBus` and add `/social/message` endpoint to `service.py`.
- [ ] Create a system entry point (`main.py`) to orchestrate the initialization sequence.
- [ ] Extend `MarketManager` and `MarketState` to provide visibility into active bids.

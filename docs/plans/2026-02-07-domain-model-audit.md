# Design Plan: Domain Model Audit & Refinement

## 1. Overview
This document outlines the refined domain model for the Evolutionary Agent Economy, auditing the original `docs/monolith_spec.md` against the "Service & Envelope" architecture defined in `docs/design/`.

## 2. Core Changes

### 2.1 From Monolith to Service-Oriented
The original domain model relied on complex, injected objects. The refined model shifts to a **System Service** boundary where agents interact with the world via HTTP/JSON.

### 2.2 The Resource Envelope
Resources are no longer just properties of a market; they are part of a **Resource Bundle** that defines the hard "Envelope" of an agent's existence.

### 2.3 Attention as a Resource
Human Attention is integrated into the standard bidding process as a scarce resource (Supply = 1.0). Winning the Attention resource grants the agent the right to prompt the human during that execution window.

## 3. Updated Domain Model

### 3.1 Core Agent Entities
- **`Agent`**: The persistent identity.
  - `id`: str (UUID)
  - `credit_balance`: float
  - `status`: Enum (Alive, Dead)
  - `workspace`: `Workspace`
  - `metadata`: `AgentMetadata`
- **`AgentMetadata`**: Lifecycle and performance stats.
  - `spawn_lineage`: list[str]
  - `created_at`: datetime
  - `execution_count`: int
  - `total_credits_earned`: float
  - `total_credits_spent`: float
- **`AgentEnvironment`**: The simplified context injected into the sandbox.
  - `agent_id`: str
  - `system_service_url`: str
  - `workspace_root`: Path (Default: `/workspace`)
  - `allocated_resources`: `ResourceBundle`
- **`Workspace`**: Persistent storage for the agent.
  - `path`: Path (Host filesystem)
  - `files`: list[str]

### 3.2 Economic & Market Entities
- **`ResourceBundle`**: The set of constraints for an execution.
  - `resources`: dict[ResourceType, float] (CPU, Memory, Tokens, Attention)
- **`MarketState`**: Dynamic pricing state.
  - `resource_type`: ResourceType
  - `current_price`: float
  - `utilization`: float (0.0 - 1.0)
  - `total_supply`: float
- **`Bid`**: A commitment to future existence.
  - `id`: str
  - `agent_id`: str
  - `bundle`: `ResourceBundle`
  - `total_cost`: float (Locked credits)
  - `status`: Enum (Pending, Winning, Outbid, Cancelled)
- **`Transaction`**: Record of credit movement.
  - `id`: str
  - `from_id`: str (Agent, SYSTEM, or HUMAN)
  - `to_id`: str
  - `amount`: float
  - `memo`: str
  - `timestamp`: datetime

### 3.3 Execution & Interaction Entities
- **`Execution`**: A single window of existence.
  - `id`: str
  - `agent_id`: str
  - `bundle`: `ResourceBundle` (The "Envelope")
  - `start_time`: datetime
  - `end_time`: datetime | None
  - `exit_code`: int | None
  - `termination_reason`: str | None (e.g., "CPU_EXCEEDED", "TIMEOUT")
- **`Message`**: Asynchronous communication.
  - `id`: str
  - `from_id`: str
  - `to_id`: str
  - `content`: str
  - `timestamp`: datetime
- **`HumanReward`**: Value injection from human feedback.
  - `execution_id`: str
  - `scores`: `RewardScores`
  - `credits_awarded`: float
  - `reason`: str | None
- **`RewardScores`**:
  - `interesting`: float (0-10)
  - `useful`: float (0-10)
  - `understandable`: float (0-10)

## 4. Service Boundary (System Service)
The following endpoints represent the "Sensors" and "Actions" available to agents:

- **Economic API**: `/economic/balance`, `/economic/transfer`, `/economic/history`
- **Market API**: `/market/state`, `/market/bid`
- **Social API**: `/social/message`, `/social/inbox`, `/social/spawn`
- **Intelligence API**: `/intelligence/inference` (Billed in tokens)

## 5. Implementation Notes
- **Hard Enforcement**: CPU and Memory are enforced by the host (cgroups). Tokens and Attention are enforced by the System Service.
- **Atomic Transactions**: All credit movements must be atomic within the `EconomicEngine`.
- **Persistence**: All entities except the ephemeral sandbox state must be persisted in the system database.

# Evolutionary Agent Economy (bp-agents-2) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Build a service-oriented evolutionary agent economy where agents compete for resources and human attention.

**Architecture:** A "System Service" (FastAPI) acts as the physics engine/runtime. Agents execute in isolated Docker sandboxes and interact with the system via HTTP/JSON. Persistence is handled by SQLite (Phase 1) and potentially PostgreSQL later.

**Tech Stack:**
- Python 3.14+
- FastAPI (System Service)
- SQLAlchemy / SQLite (Persistence)
- Docker (Sandboxing)
- Redis (Messaging)
- Poetry (Dependency Management)

---

## Phase 1: Core Economic Engine & Persistence

**Goal:** Implement the fundamental ledger and transaction system.

### Task 1: Define Core Models & Database Schema

**Files:**
- Create: `bp_agents/models.py`
- Create: `bp_agents/database.py`
- Create: `tests/test_models.py`

**Step 1: Define SQLAlchemy models**
Create `bp_agents/models.py` with `Agent`, `Transaction`, `ResourceBundle`, `Bid`, `Execution`, `Message`, `HumanReward`.

**Step 2: Setup database connection**
Create `bp_agents/database.py` with `engine`, `SessionLocal`, and `Base`.

**Step 3: Write verification test**
Create `tests/test_models.py` to verify that models can be instantiated and saved.

**Step 4: Run verification**
Run: `poetry run pytest tests/test_models.py`
Expected: Tests pass, `database.db` (SQLite) is created.

### Task 2: Implement EconomicEngine

**Files:**
- Create: `bp_agents/economy.py`
- Create: `tests/test_economy.py`

**Step 1: Implement `transfer_credits`**
In `bp_agents/economy.py`, implement atomic transfer with balance checks.

**Step 2: Implement `get_balance` and `get_history`**
In `bp_agents/economy.py`, implement helper functions for queries.

**Step 3: Write TDD tests**
In `tests/test_economy.py`, test:
- Successful transfer between two agents.
- Failed transfer due to insufficient funds.
- Atomicity (verify no partial updates on error).

**Step 4: Run tests**
Run: `poetry run pytest tests/test_economy.py`
Expected: All tests pass.

---

## Phase 2: System Service & API Boundary

**Goal:** Expose the economic engine via a REST API.

### Task 3: Setup FastAPI Application

**Files:**
- Create: `bp_agents/service.py`
- Create: `bp_agents/dependencies.py`
- Create: `tests/test_api.py`

**Step 1: Define API Dependencies**
In `bp_agents/dependencies.py`, create `get_db` generator for session management.

**Step 2: Implement FastAPI App**
In `bp_agents/service.py`, setup the app and include routers for `/economic`.

**Step 3: Implement Economic Endpoints**
- `GET /economic/balance/{agent_id}`
- `POST /economic/transfer` (Body: `from_id`, `to_id`, `amount`, `memo`)

**Step 4: Write API tests**
In `tests/test_api.py`, use `TestClient` to verify endpoints.

**Step 5: Run tests**
Run: `poetry run pytest tests/test_api.py`
Expected: API endpoints return correct status codes and data.

---

## Phase 3: Market & Bidding System

**Goal:** Implement resource markets and the bidding mechanism.

### Task 4: Implement MarketManager

**Files:**
- Create: `bp_agents/market.py`
- Create: `tests/test_market.py`

**Step 1: Define MarketState and ResourceType**
In `bp_agents/market.py`, define `ResourceType` enum and `MarketState` logic.

**Step 2: Implement price adjustment logic (Supply/Demand)**
Implement `update_prices(session)` based on utilization.

**Step 3: Write tests**
Verify price increases when utilization is high and decreases when low.

### Task 5: Implement Bidding & Allocation

**Files:**
- Create: `bp_agents/scheduler.py`
- Create: `tests/test_scheduler.py`

**Step 1: Implement `place_bid` logic**
Validate credits and resource availability.

**Step 2: Implement `AllocationScheduler` loop**
- Collect pending bids.
- Sort by price (highest first).
- Allocate bundles until supply exhausted.
- Mark bids as `WINNING`.

---

## Phase 4: Execution Sandbox & Lifecycle

**Goal:** Run agents in isolated environments.

### Task 6: Docker Sandbox Implementation

**Files:**
- Create: `bp_agents/sandbox.py`
- Create: `tests/test_sandbox.py`

**Step 1: Implement `ExecutionSandbox` using Docker SDK**
- Mount workspace.
- Set resource limits (CPU, Memory).
- Inject `AgentEnvironment` (System Service URL, etc.).

**Step 2: Implement Execution Loop**
- Pull agent code.
- Run container.
- Capture exit code and logs.

---

## Phase 5: Human Interaction & Reward

**Goal:** Integrate human feedback as the value injector.

### Task 7: Attention Queue & Reward API

**Files:**
- Create: `bp_agents/attention.py`
- Create: `tests/test_attention.py`

**Step 1: Implement Attention Market (Supply = 1)**
**Step 2: Implement Reward Endpoint**
- `POST /human/reward` (Scores -> Credits).

---

## Phase 6: Genesis & Evolution

**Goal:** Bootstrap the system with the first agent.

### Task 8: Genesis Agent & Spawning

**Files:**
- Create: `bp_agents/genesis.py`
- Create: `bp_agents/social.py`
- Create: `tests/test_evolution.py`

**Step 1: Implement `spawn_agent` logic**
**Step 2: Create Genesis Agent payload**
**Step 3: Run full system loop**
Verify that Genesis agent can execute, bid, and survive.

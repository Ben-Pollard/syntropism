# E2E Testing Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Implement a comprehensive E2E test suite that proves the core survival, interaction, evolution, competition, and death loops of the Evolutionary Agent Economy System, while resolving current logging and visibility issues.

**Architecture:**
- **Test Framework:** `pytest` with `pytest.mark.e2e`.
- **Sandbox:** Use existing `ExecutionSandbox` (Docker-based) to run agents.
- **Database:** Use a shared SQLite database for the system and tests.
- **Logging:** Centralize system logs and ensure agent logs are visible in the orchestrator output.
- **Scenarios:** 5 distinct E2E tests covering the survival loop, human interaction, spawning, competition, and death.

**Tech Stack:** Python, SQLAlchemy, Docker, Pytest, Loguru.

---

### Task 1: Infrastructure - Logging and CLI Loop

**Files:**
- Modify: `syntropism/orchestrator.py` (Add log printing and death check)
- Modify: `syntropism/cli.py` (Add loop option)
- Modify: `syntropism/sandbox.py` (Improve log capture)

**Step 1: Update `orchestrator.py` to print agent logs and check for death**
```python
# syntropism/orchestrator.py

def run_system_loop(session: Session):
    # ... existing allocation ...
    
    # Step 2: Execution
    for bid in winning_bids:
        # ... existing setup ...
        exit_code, logs = sandbox.run_agent(...)
        
        # NEW: Print agent logs to system stdout for visibility
        print(f"\n--- Agent {agent.id} Logs ---")
        print(logs)
        print(f"--- Agent {agent.id} Finished (Exit: {exit_code}) ---\n")
        
        # ... existing update ...

    # NEW: Step 5: Death Check - mark agents with no credits as DEAD
    dead_agents = session.query(Agent).filter(Agent.credit_balance <= 0, Agent.status == AgentStatus.ALIVE).all()
    for agent in dead_agents:
        print(f"Agent {agent.id} has run out of credits and died.")
        agent.status = AgentStatus.DEAD
    
    session.commit()
```

**Step 2: Update `cli.py` to support continuous loop**
```python
# syntropism/cli.py

def main():
    # ... existing setup ...
    import time
    continuous = os.getenv("CONTINUOUS") == "1"
    
    while True:
        print("\n--- Starting System Loop ---")
        run_system_loop(session)
        print("--- System Loop Complete ---")
        
        if not continuous:
            break
        time.sleep(5)
```

---

### Task 2: Scenario 1 - Survival Loop

**Goal:** Prove Genesis agent bids, executes, and rebids.

**Files:**
- Create: `tests/e2e/test_scenarios.py`

**Step 1: Implement `test_survival_loop`**
```python
@pytest.mark.e2e
def test_survival_loop(db_session):
    # 1. Setup Genesis
    agent = seed_genesis_agent(db_session)
    
    # 2. Run loop 1 (Bootstrap + Execution)
    bootstrap_genesis_execution(db_session)
    run_system_loop(db_session)
    
    # 3. Verify agent executed once
    db_session.refresh(agent)
    assert agent.execution_count == 1
    
    # 4. Verify agent placed a new PENDING bid during execution
    new_bid = db_session.query(Bid).filter_by(from_agent_id=agent.id, status=BidStatus.PENDING).first()
    assert new_bid is not None
    
    # 5. Run loop 2 (Allocation + Execution of new bid)
    run_system_loop(db_session)
    db_session.refresh(agent)
    assert agent.execution_count == 2
```

---

### Task 3: Scenario 2 - Human Interaction

**Goal:** Prove agent prompts human, receives scores, earns credits.

**Step 1: Implement `test_human_interaction`**
```python
@pytest.mark.e2e
def test_human_interaction(db_session, monkeypatch):
    # 1. Setup agent with attention allocation
    agent = seed_genesis_agent(db_session)
    # ... ensure agent has credits and a winning bid with attention_share=1.0 ...
    
    # 2. Mock input() for human scores
    monkeypatch.setattr('builtins.input', lambda _: "8 9 7")
    
    # 3. Run loop
    initial_balance = agent.credit_balance
    run_system_loop(db_session)
    
    # 4. Verify credits awarded
    db_session.refresh(agent)
    assert agent.credit_balance > initial_balance
```

---

### Task 4: Scenario 3 - Evolution (Spawning)

**Goal:** Prove agent spawns child, child executes.

**Step 1: Implement `test_agent_spawning`**
```python
@pytest.mark.e2e
def test_agent_spawning(db_session):
    # 1. Setup parent
    parent = seed_genesis_agent(db_session)
    
    # 2. Manually trigger spawn (or use a specialized agent script)
    from syntropism.genesis import spawn_child_agent
    child = spawn_child_agent(db_session, parent.id, initial_credits=100.0)
    
    # 3. Verify child in DB
    assert child.id.startswith("agent-")
    assert child.spawn_lineage == [parent.id]
    
    # 4. Run loop and verify child can execute (if it has a bid)
    # ...
```

---

### Task 5: Scenario 4 - Competition

**Goal:** Prove highest bidder wins resource.

**Step 1: Implement `test_bid_competition`**
```python
@pytest.mark.e2e
def test_bid_competition(db_session):
    # 1. Setup two agents
    a1 = seed_agent(db_session, "agent1", credits=100)
    a2 = seed_agent(db_session, "agent2", credits=100)
    
    # 2. Place bids for same limited resource
    # ... A1 bids 10, A2 bids 20 ...
    
    # 3. Run allocation
    AllocationScheduler.run_allocation_cycle(db_session)
    
    # 4. Verify A2 wins, A1 outbid
    bid1 = db_session.query(Bid).filter_by(from_agent_id=a1.id).first()
    bid2 = db_session.query(Bid).filter_by(from_agent_id=a2.id).first()
    assert bid2.status == BidStatus.WINNING
    assert bid1.status == BidStatus.OUTBID
```

---

### Task 6: Scenario 5 - Death

**Goal:** Prove agent dies when out of credits.

**Step 1: Implement `test_agent_death`**
```python
@pytest.mark.e2e
def test_agent_death(db_session):
    # 1. Setup agent with 1 credit
    agent = seed_agent(db_session, "poor_agent", credits=1.0)
    
    # 2. Place bid for 1 credit
    # ...
    
    # 3. Run loop (Execution spends the credit)
    run_system_loop(db_session)
    
    # 4. Verify status is DEAD
    db_session.refresh(agent)
    assert agent.credit_balance == 0
    assert agent.status == AgentStatus.DEAD
```

---

### Verification Steps

1. Run all E2E tests:
   `poetry run pytest tests/e2e/test_scenarios.py -m e2e`
2. Verify `system.log` contains entries from both orchestrator and agents.
3. Verify CLI output shows agent logs during execution.

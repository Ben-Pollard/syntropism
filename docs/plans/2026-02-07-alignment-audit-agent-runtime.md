# Alignment Audit: Agent Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Implement the "Pure Decoupling" architecture for agent runtime, ensuring agents are autonomous projects interacting with the system via a filesystem handshake (`env.json`) and a stable HTTP API.

**Architecture:**
- **Infrastructure**: `ExecutionSandbox` handles the `env.json` handshake.
- **Workspaces**: Persistent host-based directories in `workspaces/`.
- **Genesis Agent**: Standalone project in `agents/genesis/`.
- **API**: `bp_agents/service.py` covers all required agent actions.

**Tech Stack:** Python, Docker, FastAPI, SQLAlchemy.

---

### Task 1: Infrastructure - `env.json` Handshake

**Files:**
- Modify: `bp_agents/sandbox.py`
- Test: `tests/test_sandbox.py`

**Step 1: Update `ExecutionSandbox.run_agent` signature**
Modify `bp_agents/sandbox.py` to accept `runtime_data: dict`.

```python
<<<<<<< SEARCH
    def run_agent(self, agent_id: str, workspace_path: str, resource_bundle: ResourceBundle):
=======
    def run_agent(self, agent_id: str, workspace_path: str, resource_bundle: ResourceBundle, runtime_data: dict = None):
>>>>>>> REPLACE
```

**Step 2: Implement `env.json` writing**
In `run_agent`, write `runtime_data` to `env.json` in the workspace before starting the container.

```python
        import json
        if runtime_data:
            env_json_path = os.path.join(workspace_path, "env.json")
            with open(env_json_path, "w") as f:
                json.dump(runtime_data, f, indent=2)
```

**Step 3: Update tests**
Modify `tests/test_sandbox.py` to verify `env.json` creation.

**Step 4: Run tests**
Run: `poetry run pytest tests/test_sandbox.py`
Expected: All tests pass.

---

### Task 2: Workspaces - Persistent Host-Based Directories

**Files:**
- Modify: `bp_agents/genesis.py`

**Step 1: Update workspace path logic**
Modify `_create_agent_with_workspace` to use `workspaces/` in the project root.

```python
<<<<<<< SEARCH
    agent = _create_agent_with_workspace(
        session=session, credit_balance=1000.0, spawn_lineage=[], filesystem_path="/tmp/genesis"
    )
=======
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    os.makedirs(workspace_root, exist_ok=True)
    agent = _create_agent_with_workspace(
        session=session, credit_balance=1000.0, spawn_lineage=[], filesystem_path=os.path.join(workspace_root, "genesis")
    )
>>>>>>> REPLACE
```

**Step 2: Update `spawn_child_agent` path**
Use `workspaces/agent-{child_id}`.

**Step 3: Verify directory creation**
Run a script to create genesis agent and check if `workspaces/genesis` exists.

---

### Task 3: API Completion - Social and Market Actions

**Files:**
- Modify: `bp_agents/service.py`

**Step 1: Add `MessageRequest` and `BidRequest` schemas**
Add to `bp_agents/service.py`.

**Step 2: Implement `POST /social/message`**
Endpoint to allow agents to send messages to each other.

**Step 3: Implement `POST /market/bid`**
Endpoint to allow agents to bid on resource bundles via `AllocationScheduler`.

**Step 4: Verify API endpoints**
Run: `poetry run uvicorn bp_agents.service:app --reload` and test with `curl`.

---

### Task 4: Agent Runtime & Genesis Code

**Files:**
- Create: `runtime/pyproject.toml`
- Create: `runtime/Dockerfile`
- Create: `workspaces/genesis/main.py`

**Step 1: Create `runtime/pyproject.toml`**
Define the standardized runtime environment.

**Step 2: Create `runtime/Dockerfile`**
Build the `bp-agent-runner` image using Poetry.

**Step 3: Build the image**
Run: `docker build -t bp-agent-runner:latest runtime/`

**Step 4: Create `workspaces/genesis/main.py`**
Implement a minimal agent that reads `env.json` and calls the API.

```python
import json
import os
import requests

def main():
    if not os.path.exists("env.json"):
        print("Error: env.json not found")
        return

    with open("env.json", "r") as f:
        env = json.load(f)
    
    print(f"Genesis Agent {env['agent_id']} active.")
    print(f"Balance: {env['credits']}")
    
    service_url = os.getenv("SYSTEM_SERVICE_URL")
    if service_url:
        try:
            res = requests.get(f"{service_url}/economic/balance/{env['agent_id']}")
            print(f"API Check: {res.json()}")
        except Exception as e:
            print(f"API Error: {e}")

if __name__ == "__main__":
    main()
```

---

### Task 5: Verification - Filesystem-as-API Handshake

**Files:**
- Create: `tests/test_audit_runtime.py`

**Step 1: Write integration test**
Test that `run_agent` correctly prepares the environment and runs the `bp-agent-runner` image with the genesis agent code.

**Step 2: Run all tests**
Run: `poetry run pytest`
Expected: All tests pass, including new runtime tests.

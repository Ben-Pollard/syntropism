# Alignment Audit: Agent Runtime & Genesis Project
**Date**: 2026-02-07
**Status**: Resolved

## Identified Gaps

### 1. Muddy Runtime Boundaries
- **Gap**: The initial implementation and spec were ambiguous about whether the system should provide an SDK inside the agent's sandbox.
- **Resolution**: **Pure Decoupling**. The system is a host/referee. The agent is an autonomous project. No system code (SDK) exists inside the agent's workspace.

### 2. Genesis Agent as System Code
- **Gap**: The genesis agent was being created as a database record with no code, or with code managed by the system's `genesis.py`.
- **Resolution**: The Genesis agent is a **separate project** in `agents/genesis/` with its own `main.py`. It is the first "user" of the system.

### 3. Ephemeral Workspaces
- **Gap**: Workspaces were being created in `/tmp`, which is not ideal for the "host filesystem" vision.
- **Resolution**: Workspaces will live in a `workspaces/` directory in the project root, allowing for human inspection and persistent agent projects.

## Clarified Vision

### The "Pure Decoupling" Architecture
1.  **System Interface (Input)**: Before each execution, the system writes a structured `env.json` file to the agent's workspace. This contains all necessary runtime data (credits, market prices, inbox).
2.  **System Interface (Actions)**: Agents perform actions (bidding, transfers, spawning) exclusively via a stable HTTP API (`SYSTEM_SERVICE_URL`).
3.  **Agent Autonomy**: The agent is wholly defined in its workspace. It manages its own internal logic, libraries, and state.
4.  **Hardened Runtime**: The system provides a standard, hardened Docker image (`bp-agent-runner`) that agents are mounted to.

### The `env.json` Schema (Draft)
```json
{
  "agent_id": "string",
  "credits": "float",
  "system_time": "ISO8601",
  "markets": {
    "resource_type": {
      "price": "float",
      "utilization": "float"
    }
  },
  "inbox": [
    {
      "from": "string",
      "content": "any",
      "timestamp": "ISO8601"
    }
  ],
  "execution_context": {
    "cpu_seconds": "float",
    "memory_mb": "float",
    "tokens": "int"
  }
}
```



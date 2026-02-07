## The Core Problems

**1. Agent code visibility**
- You need to see/audit what agents are running
- Agents need to modify their own code
- Can't trust agents to report code accurately

**2. Sandbox vs. persistence**
- Agents execute in sandboxes (isolated, temporary)
- But their code/state must persist (survive between executions)
- Your filesystem vs. sandbox filesystem


## Proposed Architecture

### Agent Composition

```python
Agent:
  - id: unique identifier
  - credit_balance: float
  - workspace: Workspace  # where agent's code/data lives
  - state: AgentState  # persistent state between executions
  - runtime: ExecutionRuntime  # how agent currently executes
```

### Workspace

```python
Workspace:
  - agent_id: str
  - filesystem_path: Path  # on YOUR filesystem
  - files: dict[str, File]
    - "main.py"  # agent's current logic
    - "state.json"  # agent's persistent data
    - "memory.db"  # if agent wants a database
    - "notes.md"  # agent's scratchpad
```

**Critical properties:**
- Lives on your filesystem: `/workspaces/agent_42/`
- You can inspect anytime: `ls /workspaces/agent_42/`
- Agents modify it during execution
- Changes persist between executions
- **Sandbox mounts workspace read/write**

**Execution flow:**
```
1. Allocation scheduler: Agent_42 wins bid
2. Create sandbox container
3. Mount /workspaces/agent_42 → /workspace (in container)
4. Execute agent's main.py from workspace
5. Agent can modify /workspace/* during execution
6. Execution ends, sandbox destroyed
7. Changes to /workspace persist (on your filesystem)
8. Next execution: mount same workspace again
```

**Benefits:**
- You see all agent code: `cat /workspaces/agent_42/main.py`
- Agents can't lie about their code (you have source of truth)
- Changes persist naturally (filesystem)
- Isolation (sandbox) + persistence (host mount)

### AgentState (Structured Persistence)

```python
AgentState:
  - agent_id: str
  - execution_count: int  # how many times agent has run
  - total_tokens_used: int
  - spawn_lineage: list[str]  # parent, grandparent, ...
  - custom_data: dict  # agent can store anything
  
  # Persisted in workspace/state.json
  # Agent reads/writes during execution
  # System also reads (for metrics, auditing)
```

**Why separate from Workspace:**
- State is structured data (JSON/DB)
- Workspace is files (code, data, scratch)
- System needs to read state efficiently
- Agents control state content

### SystemEnvironment (Shared Context)

```python
SystemEnvironment:
  - markets: dict[ResourceType, MarketState]
  - economy_config: EconomyConfig
  - allocation_schedule: float
  - current_time: datetime
  - agent_directory: list[str]
  
  # Shared across all agents
  # Read-only from agent perspective
  # Updated by system
```

### AgentEnvironment (Agent-Specific Context)

```python
AgentEnvironment:
  - system: SystemEnvironment  # composed
  - self_state: AgentState  # agent's own state
  - inbox: list[Message]  # agent's messages
  - workspace_path: Path  # where agent's files are
  - execution_context: ExecutionContext  # current execution limits
  
  # NEW: Introspection access
  - introspection: IntrospectionAPI  # optional, costs tokens
```

**Composition:**
```python
# System creates agent environment for each execution
def create_agent_environment(agent_id: str) -> AgentEnvironment:
    return AgentEnvironment(
        system=global_system_environment,  # shared
        self_state=load_agent_state(agent_id),  # agent-specific
        inbox=load_messages(agent_id),  # agent-specific
        workspace_path=f"/workspaces/{agent_id}",
        execution_context=current_execution_limits,
        introspection=IntrospectionAPI(agent_id)  # if agent pays for it
    )
```

### Sensors (Explicit Observation Layer)

```python
Sensors:
  """What agent can observe (beyond environment)"""
  
  def observe_markets(self) -> dict[ResourceType, MarketState]:
      """See current market state"""
  
  def observe_agents(self) -> list[str]:
      """See other agents (IDs only)"""
  
  def observe_workspace(self) -> list[Path]:
      """See own files"""
  
  def read_file(self, path: str) -> str:
      """Read from workspace"""
  
  def observe_system_source(self, component: str) -> str:
      """Read system code (costs tokens)"""
```

**Why explicit sensors:**
- Makes observation costs clear
- Agent chooses what to observe (context management)
- Using sensors costs tokens from their current run budget
- Familiar pattern from RL/agent literature

## Filesystem Strategy

Execution sandbox mounts:
1. /host/workspaces/{agent_id} → /workspace (read-write, agent's files)
2. /host/system_code → /system (read-only, system source code)

Host filesystem:
/project/
  ├── system_code/          # System implementation
  │   ├── economic_engine.py
  │   ├── market_manager.py
  │   ├── allocation_scheduler.py
  │   └── ...
  ├── workspaces/           # Agent workspaces
  │   ├── agent_42/
  │   │   ├── main.py
  │   │   └── state.json
  │   ├── agent_89/
  │   │   └── ...
  │   └── ...
  └── config/
      └── economy.yaml

Container view (during agent execution):
/
├── workspace/              # Agent's own files (read-write)
│   ├── main.py
│   └── state.json
└── system/                 # System code (read-only)
    ├── economic_engine.py
    ├── market_manager.py
    └── ...


**Agent workspace**
```
Execution:
1. Create sandbox
2. Mount /host/workspaces/agent_42 → /sandbox/workspace (bind mount)
3. Mount /host/system_code → /system (read-only, system source code)
3. Agent modifies /sandbox/workspace/*
4. Changes immediately visible on host
5. Sandbox destroyed, files persist
```

**Benefits:**
- Single source of truth (host filesystem)
- No sync needed
- You can watch changes live: `watch cat /workspaces/agent_42/main.py`
- Standard container pattern (Docker volumes)

**Security:**
- Agent can only modify its own workspace
- Can't escape to rest of your filesystem
- Sandbox enforces path constraints



## Example: Agent Modifying Itself

**Agent wants to improve its bidding strategy:**

```python
# In agent's main.py (running in sandbox)
def execute(env: AgentEnvironment):
    # Read current strategy
    current_code = env.workspace.read_file("main.py")
    
    # Use LLM to improve
    improved_code = env.sensors.llm_call(f"""
    Here's my current code:
    {current_code}
    
    Improve the bidding logic to be more efficient.
    """)
    
    # Write new version
    env.workspace.write_file("main.py", improved_code)
    
    # Next execution will use improved code!
```

**You observe:**
```bash
# Watch agent self-modify
watch -n 1 'cat /workspaces/agent_42/main.py'

# See the diff
git diff /workspaces/agent_42/main.py

# Audit history
cd /workspaces/agent_42
git log  # if workspace is git repo
```

# Agent wants to understand allocation algorithm
```python
def execute(env: AgentEnvironment):
    # Read system code (costs ~500 tokens)
    scheduler_code = env.sensors.read_system_source("allocation_scheduler")
    
    # Analyze with LLM
    analysis = env.sensors.llm_call(f"""
    Here's the allocation scheduler code:
    {scheduler_code}
    
    I'm losing bids frequently. Analyze the algorithm and suggest
    a better bidding strategy for me.
    """)
    
    # Update own strategy based on analysis
    improved_strategy = generate_strategy(analysis)
    env.workspace.write_file("main.py", improved_strategy)
```

## Hot reload support - System can detect changes and reload
```python
import importlib
import watchdog

def on_system_file_changed(filepath):
    module = filepath_to_module(filepath)
    importlib.reload(module)
    logger.info(f"Reloaded {module}")
```

**Standard agentic patterns we should adopt:**
- ✅ Sensors (observation)
- ✅ Actions (what agent can do)
- ✅ State (persistence between episodes/executions)
- ✅ Environment (context provided to agent)
- ❌ Rewards (we use credits instead)
- ❌ Policy (agent logic is freeform, not fixed policy)

## Updated Domain Model Section

**Add to specification:**

### Agent Workspace
```
Workspace:
  - agent_id: str
  - filesystem_path: Path  # /workspaces/{agent_id} on host
  - mounted_in_sandbox: Path  # /workspace in container
  
Files in workspace for genesis agent:
  - main.py (required) - agent's execution logic
  - state.json (optional) - structured state
  - [any other files agent creates]

Properties:
  - Lives on host filesystem (visible to human)
  - Mounted into sandbox during execution
  - Agent can read/write files during execution
  - Changes persist between executions
  - Human can inspect/audit anytime
```



**Key decisions:**
1. ✅ Direct mount (not sync) for workspace
2. ✅ Workspace on your filesystem (transparency)
3. ✅ Separate concerns (workspace, state, environment)
4. ✅ Explicit sensors (observation costs)
5. ✅ Composition (SystemEnvironment → AgentEnvironment)
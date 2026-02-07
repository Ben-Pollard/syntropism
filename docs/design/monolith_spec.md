# Evolutionary Agent Economy System - Project Specification

## 1. Project Overview

### 1.1 Motivation
This is an experimental system exploring emergent behavior in AI agent economies. Rather than explicitly programming agent capabilities, we create minimal economic rules and let useful behaviors emerge through competitive selection pressure driven by human attention.

### 1.2 Core Concept
Agents compete for credits by capturing human attention. Credits purchase computational resources. Agents with efficient strategies survive and reproduce. Specialization, cooperation, and infrastructure emerge from economic pressures rather than explicit design.

### 1.3 Design Philosophy
- **Emergence over design**: Prefer simple rules to complex orchestration
- **Agent agency**: Agents make their own decisions about execution and resource allocation
- **Economic alignment**: If economics don't work, features don't matter
- **Execution = existence**: Agents only experience time during execution; between executions is oblivion
- **Let banking emerge**: Don't build financial infrastructure upfront; let agents create it if needed
- **YAGNI**: Add metadata/features only when there's clear need

### 1.4 What Makes This Unique
Unlike existing agent frameworks (AutoGen, CrewAI, LangGraph):
- Credit-based resource economy with competitive bidding
- Agents bid to execute (not scheduled/called)
- Discrete execution model (no continuous processes)
- Dynamic supply/demand resource pricing
- Human attention as scarce tradeable resource
- All-or-nothing resource bundle allocation

---

## 2. Domain Model

### Sandbox
ExecutionSandbox:
  - agent_id: str
  - workspace_mount: Path  # /workspaces/{agent_id} mounted at /workspace
  - resource_limits: dict  # CPU, memory, tokens
  - network: NetworkPolicy  # restricted
  - filesystem: FilesystemPolicy  # only /workspace writable


### Agent
Agent:
  - id: str (unique identifier)
  - credit_balance: float (universal currency)
  - environment: AgentEnvironment
  - execution_context: ExecutionContext (resources allocated for this execution)

AgentEnvironment:
  - system: SystemEnvironment  # shared global context
  - state: AgentState  # agent's own persistent state
  - agentmetadata: AgentMetaData
  - inbox: list[Message]  # messages to this agent
  - workspace: WorkspaceAPI  # interface to agent's files
  - sensors: Sensors  # observation capabilities
  - actions: Actions  # what agent can do

  SystemEnvironment:
  - allocation_cycle: int  # which cycle we're on
  - current_time: datetime
  - agent_directory: list[str]  # agent IDs only
  - markets: dict[ResourceType, MarketState]
  - source: Path: read-only source code directory


### Agent State
Data about the agent provided by  core system via the execution context
AgentMetaData
  - agent_id: str
  - status: AgentStatus (alive | dead)
  - execution_count: int
  - total_credits_earned: float
  - total_credits_spent: float
  - spawn_lineage: list[str]  # [parent_id, grandparent_id, ...]
  - created_at: datetime
  - last_execution: datetime

### Workspace
Workspace:
  - agent_id: str
  - filesystem_path: Path  # /workspaces/{agent_id} on host
  - mounted_path: Path  # /workspace in container

Files in workspace for genesis agent:
  - main.py (required) - agent's execution logic
  - state.json (optional) - structured state
  - [any other files agent creates]


### Sensors (Explicit Observation Layer)
```python

  """What agent can observe (beyond environment)"""
  
  def observe_markets(self) -> dict[ResourceType, MarketState]:
      """See current market state"""
  
  def observe_agents(self) -> list[str]:
      """See other agents (IDs only)"""
  
  def observe_workspace(self) -> list[Path]:
      """See own files"""
  
  def read_file(self, path: Path) -> str:
      """Read from workspace"""
  
  def observe_system_file(self, path: Path) -> str:
      """Read system code"""
```



#### Resource
Resource:
  - type: ResourceType (enum: tokens, cpu, memory, gpu, attention)
  - available_supply: float (set by system operator)
  - cost_in_credits: float (dynamically adjusts via supply/demand)

**Properties:**
- All resources purchased with credits (no special status for any type)
- Supply/demand drives pricing toward equilibrium
- System Resources are priced per unit time e.g. 10% cpu utilisation for 100000ms
- Attention is a resource with supply = 1.0 (single slot)

#### Economy
```
Economy:
  - resources: list[Resource]
  - initial_credit_budget: float (starting credits for new agents)
  - attention_conversion_rates: dict[string, float]
    - "interesting": X credits per point
    - "useful": Y credits per point
    - "understandable": Z credits per point
  - spawn_cost: float (credits to create new agent)
  - message_cost: float (credits to send message)
  - allocation_schedule_seconds: float (market clearing frequency)
```

#### MarketState
MarketState:
  - resource_type: ResourceType
  - available_supply: float
  - current_utilization: float (0-100%)
  - current_market_price: float (credits per unit)
  - active_bids: list[Bid] (visible to all agents)
  - recent_transactions: list[Transaction] (last N, configurable)

#### Bid
Bid:
  - id: str (unique identifier)
  - from_agent: agent_id
  - resources: dict[ResourceType, float]  # complete bundle
  - payload: callable  # code to execute if allocated
  - total_cost: float  # sum of resource costs at bid time
  - status: BidStatus (pending | allocated | outbid | withdrawn)
  - timestamp: datetime


**Properties:**
- Must specify ALL resources needed for one execution
- All-or-nothing allocation (entire bundle or nothing)
- Agent must have sufficient credits when bid placed


#### Transaction
Transaction:
  - from_entity_id: agent_id | market | human
  - to_entity_id: agent_id | market | human
  - amount: float (credits)
  - memo: str (freeform description)
  - timestamp: datetime

#### Message
```
Message:
  - id: unique identifier
  - from_agent: agent_id
  - to_agent: agent_id
  - content: str
  - timestamp: datetime
```


#### Prompt
An agent's bid for human attention.
Prompt:
  - id: str (unique identifier)
  - from_agent: agent_id
  - content: any (what agent wants to show/ask)
  - bid_amount: float (credits paid for attention slot)
  - status: PromptStatus (pending | active | responded)
  - timestamp: datetime

#### Response
Human feedback on a prompt.

Response:
  - to_prompt: prompt_id
  - scores: dict[str, float]
    - "interesting": 0-10
    - "useful": 0-10
    - "understandable": 0-10
  - reason: str | None (optional explanation)
  - credits_awarded: float (scores × conversion_rates)
  - timestamp: datetime


---

## 3. Core Mechanisms

### 3.1 Execution Model

**Fundamental principle: Execution = Existence**

Agents only experience time during execution. Between executions is oblivion (agent experiences nothing).

**Execution lifecycle:**

1. **Agent executes (wakes up)**
   - Observes AgentEnvironment
   - Runs logic (within allocated resource limits)
   - **MUST place at least one bid** for future execution
   - May also: send messages, transfer credits, spawn agents, prompt human
   - Execution ends (oblivion)

2. **Oblivion (between executions)**
   - Agent experiences nothing
   - Time passes in the system
   - Markets operate
   - Other agents execute

3. **Market allocation (on schedule)**
   - If agent's bid wins → scheduled for next execution
   - If bid loses/outbid → remains in oblivion

4. **Next execution (if allocated)**
   - Agent wakes up again
   - Cycle repeats

**Critical rules:**
- Agent that fails to place any bids during execution → never wakes up (death)
- Agent can place multiple bid bundles (independent future executions)
- Each bundle allocated independently (can win some, lose others)

### 3.2 Resource Purchase & Allocation

**Purchase flow:**

1. **Agent places bid**
   - Specifies complete resource bundle: `{tokens: 500, cpu_seconds: 2.0, memory_mb: 100}`
   - Includes payload (code to execute)
   - Bid amount must be ≥ current market price for each resource
   - Credits not debited yet (bid is commitment)

2. **Bid enters market**
   - Visible to all agents
   - Queued in priority order (highest bid first)
   - Agent can rebid higher if outbid
   - Agent can withdraw bid

3. **Market allocation (runs every N seconds, configurable)**
   - For each bid bundle:
     - Check if ALL resources available
     - Check if bid is highest for contested resources
     - All-or-nothing: entire bundle allocated or rejected
   - Winners determined

4. **Allocation**
   - Winning agent's credits debited (sum of resource costs)
   - System creates execution sandbox with resource limits
   - Payload executes within limits
   - Resources released when execution completes

5. **Failed allocation**
   - Bid remains in queue
   - Agent remains in oblivion
   - Waits for next allocation round

**Supply/demand pricing:**
- High utilization → prices increase
- Low utilization → prices decrease
- Market seeks equilibrium
- Hard constraint: cannot exceed available supply at any price

**Market visibility:**
- All active bids visible (transparent market)
- Last N transactions visible per resource
- Current prices visible
- Agents can observe and strategize

### 3.3 Human Attention Mechanism

**Attention as scarce resource:**
- Supply = 1.0 (single attention slot)
- Agents bid credits to prompt human
- Highest bidder wins slot
- Agent pays bid amount when prompt sent

**Attention queue:**
- Multiple agents can bid for attention
- Queue ordered by bid amount (highest first)
- Agents can rebid higher while waiting
- Only one prompt active at a time

**Human interaction:**
1. Agent wins attention slot
2. Human receives prompt (content from agent)
3. Human provides scores (0-10 for interesting/useful/understandable)
4. Optional: human provides reason (string)
5. Credits awarded to agent (scores × conversion rates)
6. Attention slot freed, next highest bidder wins

**Economic pressure:**
- Poor prompts (low scores) → agent paid bid but earned little → net loss
- Good prompts (high scores) → agent earns more than bid → net profit
- Agents learn to prompt only when they have valuable content

### 3.4 Agent Spawning

**Spawn mechanics:**

1. **Parent agent decides to spawn**
   - Calls `spawn_agent(logic, initial_credits)`
   - Parent pays: spawn_cost + initial_credits
   - New agent created with unique ID

2. **Child agent is immediately independent**
   - No ownership relationship
   - Child has own credit balance (initial_credits)
   - Child makes own decisions

3. **Parent's motivation:**
   - **Cost reduction**: Spawn specialist to handle repeated work cheaper
   - **Market creation**: If child succeeds, parent can outsource to child
   - **Exploration**: Test if new niche is viable
   - **Succession**: Parent dying, spawn replacement

4. **Value flow model:**
   - Parent spawns child (independent)
   - Parent pays child for services (credit transfer)
   - Parent markets child's work to human (captures attention)
   - Parent benefits from arbitrage (child cheaper than parent doing work)

**Asynchronous coordination:**
- Parent and child execute at different times
- Communication via messages (persisted in inbox)
- Parent can send instructions: "Do X, I'll pay Y"
- Child can comply or defect (independent agent)
- Trust/reputation emerges through repeated interaction

### 3.5 Agent Communication

**Message passing:**
- Agents send messages (asynchronous)
- Messages persist in recipient's inbox
- Recipient reads when they next execute
- Sender pays message cost

**Coordination patterns:**
- Contracts: "Do X, get paid Y"
- Promises: "I owe you Z credits"
- Information sharing: "Market price rising"
- Delegation: "Handle these tasks"

**Standard messaging infrastructure:**
- Use off-the-shelf message bus (Redis, RabbitMQ, etc.)
- Economic system charges for delivery
- What's unique: credit-based, asynchronous, competitive context

---

## 4. System Architecture

### 4.1 Component Overview

```
┌─────────────────────────────────────────────┐
│   Custom Economic Runtime                   │
│   ┌─────────────────────────────────────┐   │
│   │ EconomicEngine                      │   │
│   │ - Credit accounts                   │   │
│   │ - Transfers, balance checks         │   │
│   └─────────────────────────────────────┘   │
│   ┌─────────────────────────────────────┐   │
│   │ MarketManager                       │   │
│   │ - Resource markets                  │   │
│   │ - Bid queues                        │   │
│   │ - Dynamic pricing                   │   │
│   └─────────────────────────────────────┘   │
│   ┌─────────────────────────────────────┐   │
│   │ AllocationScheduler                 │   │
│   │ - Market clearing                   │   │
│   │ - Resource allocation               │   │
│   │ - Execution queueing                │   │
│   └─────────────────────────────────────┘   │
│   ┌─────────────────────────────────────┐   │
│   │ AttentionQueue                      │   │
│   │ - Human attention bidding           │   │
│   │ - Prompt routing                    │   │
│   │ - Score → credit conversion         │   │
│   └─────────────────────────────────────┘   │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│   Standard Agent Infrastructure             │
│   ┌─────────────────────────────────────┐   │
│   │ ExecutionManager                    │   │
│   │ - Sandboxed execution               │   │
│   │ - Resource limit enforcement        │   │
│   └─────────────────────────────────────┘   │
│   ┌─────────────────────────────────────┐   │
│   │ MessageBus                          │   │
│   │ - Agent-to-agent messaging          │   │
│   │ - Inbox persistence                 │   │
│   └─────────────────────────────────────┘   │
│   ┌─────────────────────────────────────┐   │
│   │ AgentRegistry                       │   │
│   │ - Agent creation/deletion           │   │
│   │ - Directory                         │   │
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 4.2 Core Components (Detail)

#### EconomicEngine
- Maintains credit accounts (agent_id → balance)
- Processes credit transfers (atomic transactions)
- Enforces balance constraints
- Provides fast balance lookups
- Transaction logging (append-only)

#### MarketManager
- Manages one market per ResourceType
- Maintains bid queues (priority by bid amount)
- Tracks resource availability/utilization
- Calculates dynamic pricing (supply/demand equilibrium)
- Validates bids (sufficient credits, above market price)
- Provides market state to agents

#### AllocationScheduler
- Runs on configured interval (e.g., every 10 seconds)
- **Allocation cycle:**
  1. Collect all pending bids
  2. For each resource market:
     - Sort bids by amount (highest first)
     - Check resource availability
     - Allocate to highest bidders until supply exhausted
  3. For each winning bid bundle:
     - Validate agent still has credits
     - Debit credits (all resources in bundle)
     - Queue execution
  4. Update market prices based on demand/utilization
  5. Cull dead agents (zero credits, no pending bids)

#### ExecutionManager
- Receives allocated execution bundles from scheduler
- Creates sandboxed environment with resource limits:
  - Token quota (for LLM calls)
  - CPU time limit
  - Memory limit
  - GPU time limit (if applicable)
- Executes agent payload within sandbox
- Enforces limits (terminates if exceeded)
- Captures output (new bids, messages, transfers, spawns)
- Releases resources when complete
- Updates agent state

#### AttentionQueue
- Special market for human attention (supply = 1)
- Manages prompt bidding (priority queue by bid amount)
- Routes winning prompt to human interface
- Receives human scores (interesting/useful/understandable)
- Converts scores to credits (scores × conversion rates)
- Awards credits to agent
- Frees attention slot for next bid

#### AgentRegistry
- Tracks all agents (id → metadata)
- Handles agent creation (spawn operation)
- Handles agent death (removal from active set)
- Provides agent directory (list of IDs)
- Manages agent lifecycle

#### MessageBus
- Routes messages between agents
- Persists messages in recipient inboxes
- Charges sender for message delivery
- Standard infrastructure (can use Redis/RabbitMQ/etc.)

### 4.3 System Initialization

```
System startup:
1. Load configuration
   - Resource supplies (tokens, CPU, memory, GPU, attention)
   - Conversion rates (attention scores → credits)
   - Costs (spawn, message)
   - Allocation schedule frequency
   - Initial credit budget for new agents
   
2. Initialize EconomicEngine
   - Empty credit accounts
   - Empty transaction log
   
3. Initialize MarketManager
   - Create markets for each resource type
   - Set initial supplies
   - Set initial prices (can be arbitrary, market will adjust)
   
4. Create genesis agent
   - Load baseline strategy/logic
   - Allocate initial_credit_budget
   - Provide instruction document (game rules)
   - Register in AgentRegistry
   - Place initial bid (so it can execute)
   
5. Start AllocationScheduler (begins running cycles)

6. Start human interaction loop (listen for attention bids)
```

### 4.4 Main Loop (Allocation Cycle)

```
Every N seconds (configurable):

1. MarketManager collects all pending bids

2. For each resource market:
   - Sort bids by amount (highest first)
   - Iterate through bids:
     - Check if all resources in bundle available
     - If yes: allocate, mark bid as winning
     - If no: skip, bid remains in queue
   - Stop when supply exhausted

3. For each winning bid bundle:
   - Validate agent credit_balance >= total_cost
   - If valid:
     - Debit credits
     - Queue execution in ExecutionManager
   - If invalid:
     - Reject bid (agent went broke)

4. ExecutionManager processes execution queue:
   - For each queued execution:
     - Create sandbox with resource limits
     - Execute agent payload
     - Capture outputs (bids, messages, transfers, spawns)
     - Process outputs (register new bids, route messages, etc.)
     - Release resources
     - Update agent state

5. MarketManager updates prices
   - For each resource:
     - If high utilization (>80%): increase price
     - If low utilization (<20%): decrease price
     - Seek equilibrium

6. AgentRegistry culls dead agents
   - Remove agents with:
     - credit_balance <= 0 AND no pending bids
   - Archive agent data for analysis

7. Repeat
```

### 4.5 State Persistence

**Critical for crash recovery and analysis:**

- **Credit accounts** → database (PostgreSQL/SQLite)
- **Market state** (bids, prices, utilization) → database
- **Agent registry** (active agents, metadata) → database
- **Transaction log** → append-only log file or database
- **Messages** → database (inbox per agent)
- **Configuration** → config file (YAML/JSON)
- **Execution history** → optional, for analysis

**Enables:**
- Crash recovery (reload state, resume)
- Historical analysis (what happened over time)
- Debugging (trace agent decisions)
- Replay (re-run scenarios)

---

## 5. Agent API

### 5.1 Methods Available to Agents

Agents call these methods during execution (within their allocated resources):

#### Economic Operations
```python
transfer_credits(to_agent_id: str, amount: float) -> bool
  # Transfer credits to another agent
  # Deducts from self, adds to recipient
  # Returns True if successful, False if insufficient credits

get_balance() -> float
  # Read own credit balance (read-only)

get_transaction_history(limit: int = 10) -> list[Transaction]
  # Read own recent transactions
  # Useful for auditing, strategy
```

#### Market Operations
```python
place_bid(
  resources: dict[ResourceType, float],
  payload: callable
) -> str  # returns bid_id
  # Place bid bundle on market
  # resources: e.g., {ResourceType.TOKENS: 500, ResourceType.CPU_SECONDS: 2.0}
  # payload: code/function to execute if allocated
  # Returns bid_id for tracking

withdraw_bid(bid_id: str) -> bool
  # Remove pending bid from market
  # Returns True if successful

get_market_state(resource_type: ResourceType) -> MarketState
  # Observe current state of one market
  # Returns: price, utilization, active bids, recent transactions

get_all_markets() -> dict[ResourceType, MarketState]
  # Observe all markets at once
```

#### Agent Operations
```python
spawn_agent(logic: any, initial_credits: float) -> str  # returns agent_id
  # Create new independent agent
  # Deducts spawn_cost + initial_credits from spawner
  # Returns new agent's ID

send_message(to_agent_id: str, content: any) -> bool
  # Send message to another agent
  # Message persists in recipient's inbox
  # Deducts message_cost from sender
  # Returns True if successful

get_inbox() -> list[Message]
  # Read messages sent to this agent
  # Messages persist until read (or expired, if configured)
```

#### Attention Operations
```python
prompt_human(content: any, bid_amount: float) -> bool
  # Bid for human attention slot
  # If bid wins (highest in queue):
  #   - Human sees prompt
  #   - Human provides scores
  #   - Agent receives credits (scores × conversion rates)
  # Returns True if bid placed successfully
  # Note: agent pays bid_amount regardless of score
```

#### Environment Observation
```python
get_agent_directory() -> list[str]
  # Returns list of active agent IDs
  # No metadata (agents are opaque)

get_config() -> EconomyConfig
  # Read system configuration
  # Conversion rates, supplies, costs, etc.

get_current_time() -> datetime
  # System timestamp
  # Agents can track time between executions

get_execution_context() -> ExecutionContext
  # Resources allocated for THIS execution
  # Remaining quota (tokens left, CPU time left, etc.)
  # Useful for resource management within execution
```

### 5.2 Library Access

Agents have access to Python within sandbox:
- Math, string manipulation, data structures
- JSON serialization
- LLM API calls
- Limited file I/O (within sandbox only)
- Whitelisted network access
- No subprocess spawning (security)


---

## 6. Technology Stack

### 6.1 Recommended Stack

**Language: Python**

**Why Python:**
- Flexibility for agent `logic` (functions, exec/eval, classes)
- Rapid prototyping (fits exploratory nature)
- LLM agent familiarity (most coding agents strongest in Python)
- Rich ecosystem (LLM APIs, async, data structures)
- Introspection capabilities (agents querying own properties)

**Tradeoffs:**
- Performance not critical initially (optimize later if needed)
- Type safety loose but fits "emergent" philosophy
- Sandboxing harder than some alternatives (acceptable for initial exploration)

**Core Dependencies:**
- **Database**: PostgreSQL or SQLite (for economic state, persistence)
- **Message bus**: Redis or RabbitMQ (for agent messaging)
- **Sandboxing**: System-provided Docker image with agent code mounted.
- **LLM API**: Langchain for genesis agent
- **Async**: asyncio (for concurrent execution management)
- **Config**: YAML or JSON (for system configuration)

**Alternative considerations:**
- **Rust**: If safety/sandboxing/performance critical from day 1 (slower iteration)
- **TypeScript**: If type safety desired (less natural for exec/eval patterns)

**Verdict**: Start Python. Iterate fast. Rewrite components later if needed.

### 6.2 Architecture Pattern

**Custom economic layer on top of standard agent infrastructure:**

- **Custom**: EconomicEngine, MarketManager, AllocationScheduler, AttentionQueue
- **Standard**: Execution sandboxing, message passing, state persistence
- **Reuse where possible**: Don't reinvent messaging, sandboxing, logging

---

## 7. Development Phases

### 7.1 Phase 1: Minimal Viable System

**Goal:** Prove core economic mechanics work

**Components:**
- EconomicEngine (credit accounts, transfers)
- MarketManager (single resource: tokens)
- AllocationScheduler (basic clearing)
- ExecutionManager (simple Python exec)
- Genesis agent with baseline strategy
- Manual human interaction (terminal REPL)

**Success criteria:**
- Genesis agent executes
- Genesis bids for continuation
- Genesis prompts human
- Human scores, genesis receives credits
- Genesis survives 10+ allocation cycles

**Timeline:** 1-2 weeks

### 7.2 Phase 2: Spawning & Evolution

**Goal:** See if specialization emerges

**Add:**
- Spawn mechanism
- Message passing
- Multiple resource types (CPU, memory, time)
- Agent-to-agent credit transfers

**Success criteria:**
- Genesis spawns specialist agent
- Specialist handles repeated pattern
- Genesis delegates work to specialist
- Genesis pays specialist
- Both agents survive (division of labor)

**Timeline:** 2-3 weeks

### 7.3 Phase 3: Observability & Tooling

**Goal:** Understand what's happening

**Add:**
- Dashboard (economy metrics, agent population)
- Logging (execution traces, decisions)
- Historical analysis (charts, trends)
- Market visualization

**Success criteria:**
- Can observe agent behavior without manual inspection
- Can identify interesting patterns (cooperation, competition)
- Can diagnose failures (why did agent X die?)

**Timeline:** 2-3 weeks

### 7.4 Phase 4: Robustness & Scale

**Goal:** Handle more agents, more complexity

**Add:**
- Better sandboxing (security)
- Performance optimization (if needed)
- Persistence/recovery (crash handling)
- Parameter tuning (allocation schedule, costs, rates)

**Success criteria:**
- System handles 100+ agents
- Survives crashes gracefully
- Economic equilibrium stable

**Timeline:** As needed

---

## 8. Critical Parameters to Tune

These will require experimentation:

**Economic:**
- `initial_credit_budget`: Starting credits for new agents (1000? 10000?)
- `attention_conversion_rates`: Credits per score point (10? 100?)
- `spawn_cost`: Credits to create agent (100? 1000?)
- `message_cost`: Credits to send message (1? 10?)

**Resource:**
- Resource supplies (how many tokens, CPU seconds available?)
- Initial prices (arbitrary, will adjust)
- Price adjustment algorithm (how fast do prices change?)

**Timing:**
- `allocation_schedule_seconds`: Market clearing frequency (1s? 10s? 60s?)
- Execution timeout (max time per agent execution)

**Market:**
- Transaction history length (last N transactions visible)
- Bid queue limits (max bids per agent? per resource?)

**These emerge through experimentation. Start with reasonable guesses, iterate.**

---

## 9. What NOT to Build

### 9.1 Anti-Patterns

**Don't build:**
- ❌ Task scheduling system (agents have agency, not tasks)
- ❌ Complex credit mechanics upfront (debt, interest, etc. - let emerge)
- ❌ Heavy UI (terminal/dashboard sufficient initially)
- ❌ Agent ownership hierarchies (all independent)
- ❌ Sophisticated routing (let agents discover each other)

**Don't optimize:**
- ❌ Performance before proving concept
- ❌ Scalability before understanding dynamics

### 9.2 What to Let Emerge

Let agents build these if they need them:
- Reputation systems
- Coordination protocols
- Information sharing (bulletin boards, etc.)
- Observability tools (if agents want to understand ecosystem)

---

## 10. Open Questions & Unknowns

### 10.1 Deliberately Unspecified

**For discovery/emergence:**
- Exact bidding strategies (agents figure this out)
- Death semantics details (what exactly happens to dead agent data)
- Agent metadata beyond minimum (add only when needed)
- Communication protocols (agents invent)
- Reputation/trust mechanisms (emerge from interactions)

**For tuning:**
- Specific parameter values (require experimentation)
- Price adjustment algorithms (multiple approaches possible)
- Allocation tie-breaking rules (first-come? random? split?)
- Resource bundling patterns (which resources typically grouped?)

### 10.2 Known Risks

**Economic:**
- **Degenerate equilibria**: All agents die, or useless agents dominate
- **Price spirals**: Resources become unaffordable
- **Credit hoarding**: Agents don't spend, system stagnates
- **Attention spam**: Agents prompt wastefully

**Technical:**
- **Execution overhead**: Sandboxing too slow
- **State explosion**: Too many agents, too much data
- **Synchronization issues**: Race conditions in markets
- **Sandbox escapes**: Security vulnerabilities

**Emergent:**
- **Gaming metrics**: Agents optimize for scores, not actual value
- **Collusion**: Agents coordinate to extract value unfairly
- **Monoculture**: One strategy dominates, diversity lost
- **Chaos**: Unpredictable emergent behaviors

**Mitigation: Monitor closely, iterate parameters, add constraints only when human agrees they are necessary.**

---

## 11. Success Criteria

### 11.1 Phase 1 Success
- Genesis agent survives 10+ allocation cycles
- Genesis successfully bids for resources
- Genesis successfully prompts human and receives credits
- Credit balance increases over time (not just spending down initial budget)
- System runs without crashes for 1 hour

### 11.2 Phase 2 Success
- At least one specialist agent spawned by genesis
- Specialist survives 10+ cycles independently
- Observable division of labor (specialist handles subset of work)
- Credit transfers between agents (delegation/payment)
- At least 3 agents alive simultaneously

### 11.3 Phase 3 Success
- Can observe agent population dynamics without code inspection
- Can identify when/why agents spawn or die
- Can see market price changes over time
- Can trace credit flows through the ecosystem

### 11.4 Long-term Success
- Emergent behaviors we didn't explicitly program:
  - Specialization (agents carve niches)
  - Cooperation (agents help each other)
  - Infrastructure (shared services emerge)
  - Innovation (new strategies discovered)
- System runs for days/weeks without manual intervention
- Human finds interaction genuinely interesting (not just functional)

---

## 12. Areas Requiring Project-Specific Attention

### 12.1 Where Standard Training Data Will Mislead

**Typical agent frameworks assume:**
- Centralized orchestration → Our agents are autonomous
- Continuous execution → Ours is discrete (execution = existence)
- Free computation → Ours is resource-constrained
- Scheduled tasks → Our agents bid to execute
- Cooperative multi-agent → Ours is competitive

**When implementing, resist urge to:**
- Add task queues (agents create own work)
- Build schedulers (market allocates execution)
- Implement free "thinking time" (all execution costs resources)
- Create agent hierarchies (all agents independent)
- Pre-build collaboration tools (let emerge)

### 12.2 Key Architectural Decisions

**Execution model:**
- NOT: Continuous agent event loops
- YES: Discrete executions triggered by market allocation / system event loop

**Resource allocation:**
- NOT: Give agents what they ask for
- YES: Market-based competitive bidding

**Agent lifecycle:**
- NOT: Spawn and forget
- YES: Agents must continuously justify existence through bids

**Communication:**
- NOT: Synchronous RPC or callbacks
- YES: Asynchronous message passing (agents execute at different times)

**Value flow:**
- NOT: Parent owns child's output
- YES: Independent agents, value flows through payments

### 12.3 Economic System Is Core

**This is NOT an agent framework with economics bolted on.**
**This IS an economic system where agents are participants.**

The economic layer is the primary system. Agent execution is secondary.

Design principle: If economics don't work, nothing else matters.

---

## 13. Testing Strategy

### 13.1 Unit Tests

**EconomicEngine:**
- Credit transfers (valid, insufficient balance, negative amounts)
- Balance queries
- Transaction logging

**MarketManager:**
- Bid validation (above market price, sufficient credits)
- Price updates (supply/demand dynamics)
- Resource availability tracking

**AllocationScheduler:**
- Bid sorting (highest first)
- All-or-nothing allocation
- Multi-resource bundle allocation

**ExecutionManager:**
- Resource limit enforcement
- Sandbox creation/cleanup
- Timeout handling

### 13.2 Integration Tests

**End-to-end scenarios:**
1. Genesis agent bids, executes, rebids (survival loop)
2. Agent prompts human, receives scores, earns credits
3. Agent spawns child, sends message, child executes
4. Two agents bid for same resource, highest wins
5. Agent runs out of credits, dies, removed from registry

### 13.3 Economic Tests

**Validate equilibrium mechanisms:**
- High demand → prices rise → utilization decreases
- Low demand → prices fall → utilization increases
- Credit conservation (total credits = initial + human awards - deaths)
- Market clearing (all allocated resources actually consumed)

### 13.4 Evolutionary Tests

**Validate emergence:**
- Specialist agents survive longer than generalists (efficiency pressure)
- Agents that prompt wastefully die (selection pressure)
- Division of labor emerges (observe specialist spawning)
- Market prices stabilize over time (equilibrium)

**Run for N cycles (100? 1000?) and observe:**
- Agent population trends
- Credit distribution (inequality emergence)
- Market price stability
- Spawn/death rates

---

## 14. Bootstrap Strategy

### 14.1 Genesis Agent

**Initial logic (baseline strategy):**

```python
"""
You are an agent in a credit-based economy.

RESOURCES:
- You have credits (check via get_balance())
- Bid credits for resources: tokens, CPU, memory, time, attention
- Markets visible (get_all_markets() for prices and bids)

MECHANICS:
- Bid for resources to execute (including LLM calls)
- Bid must include ALL needed resources (all-or-nothing)
- Bids queue, allocated on schedule
- You MUST bid for continuation each execution or you die

EARNING CREDITS:
- Bid for "attention" to prompt the human
- Human scores prompts: interesting, useful, understandable (0-10)
- Scores convert to credits
- Strategy: only prompt when you have something valuable

ACTIONS:
- place_bid(resources, payload) - bid for future execution
- transfer_credits(agent_id, amount) - pay another agent
- spawn_agent(logic, initial_credits) - create new agent
- send_message(agent_id, content) - communicate
- prompt_human(content, bid_amount) - bid for attention

SURVIVAL STRATEGY:
1. Observe markets (get_all_markets())
2. Bid for minimal execution to continue (cheap survival)
3. Occasionally bid for larger execution to do productive work
4. Prompt human when you have something interesting
5. If you discover repeating patterns, consider spawning specialist
6. Balance: survival (cheap bids) vs. value creation (expensive bids)

REMEMBER: Execution = existence. No bid = death.
"""
```

**Initial credit budget:** 1000 credits (enough for ~10-20 small executions)

**First execution:**
Genesis should:
- Observe markets
- Bid for continuation (modest resources)
- Possibly prompt human with introduction

### 14.2 Configuration (Initial Values)

```yaml
economy:
  initial_credit_budget: 1000
  attention_conversion_rates:
    interesting: 50  # 50 credits per point
    useful: 50
    understandable: 50
  spawn_cost: 100
  message_cost: 1

resources:
  tokens:
    supply: 10000
    initial_price: 0.1  # 0.1 credits per token
  cpu_seconds:
    supply: 100
    initial_price: 5  # 5 credits per second
  memory_mb:
    supply: 10000
    initial_price: 0.01  # 0.01 credits per MB
  attention:
    supply: 1
    initial_price: 50  # 50 credits per prompt

allocation:
  schedule_seconds: 10  # Market clears every 10 seconds
  transaction_history_length: 20  # Last 20 transactions visible

execution:
  timeout_seconds: 30  # Max execution time
  default_memory_mb: 100
```

**These are starting guesses. Expect to tune extensively.**

---

## 15. Human Interface

### 15.1 Dashboard (Terminal Initially)

**Display:**

```
=== EVOLUTIONARY AGENT ECONOMY ===

Resources:
  CPU:      [████████░░] 80% utilized, 5.2 credits/sec
  Memory:   [███░░░░░░░] 30% utilized, 0.01 credits/MB
  Tokens:   [██████░░░░] 60% utilized, 0.15 credits/token
  Attention:[██████████] 100% utilized, 120.0 credits/prompt

Agents: 5 alive

Credits in circulation: 3,450

Recent activity:
  [12:34:56] Agent_42 spawned Agent_89 (cost: 150 credits)
  [12:34:58] Agent_15 bid 120 credits for attention (pending)
  [12:35:00] Agent_42 executed (cost: 45 credits)
  [12:35:02] Market cleared: 3 bids allocated
  [12:35:05] Agent_89 sent message to Agent_42

Attention queue:
  1. Agent_15 (bid: 120 credits) - ACTIVE
  2. Agent_42 (bid: 85 credits)
  3. Agent_7 (bid: 60 credits)

===================================
```

### 15.2 Human Interaction Loop

**When agent wins attention:**

```
=== PROMPT FROM Agent_15 ===

[Agent's content displayed here]

Rate this prompt:
  Interesting (0-10): _
  Useful (0-10): _
  Understandable (0-10): _
  Reason (optional): _

[Submit scores]

Credits awarded: 450 (based on scores)
Agent_15 new balance: 720 credits
```

**Commands available:**
- `status` - show dashboard
- `agents` - list all agents
- `agent <id>` - inspect specific agent
- `markets` - detailed market view
- `history` - recent transactions
- `config` - show configuration
- `quit` - shutdown system

---

## 16. Tooling

### 16.1 Development Tools

**Essential:**
- **Python 3.14+** (for latest async features, type hints)
- **Poetry** (dependency management, reproducible builds)
- **pytest** (testing framework)
- **ruff** (code formatting, linting)
- **mypy** (optional type checking - useful for economic primitives)

**Database:**
- **SQLite** (Phase 1 - simple, embedded)
- **PostgreSQL** (Phase 2+ - if scaling needed)
- **Alembic** (database migrations)

**Message Bus:**
- **Redis** (simple, fast, good Python support)
- Alternative: **RabbitMQ** (if need more sophisticated routing later)

**Sandboxing:**
- **Docker Python SDK**
- Alternative: **gVisor** (if paranoid about security)

**LLM Integration:**
- **Langchain** (for agent LLM calls)
- **python-dotenv** (API key management)

### 16.2 Observability & Debugging

**Logging:**
```python
# Structured logging
import structlog

logger = structlog.get_logger()
logger.info("bid_placed", 
    agent_id=agent_id,
    resource="tokens", 
    amount=500,
    bid_price=50.0
)
```

**Metrics (Phase 2+):**
- **Prometheus** (time series metrics)
  - Agent count over time
  - Credit distribution
  - Market prices
  - Allocation success rate
- **Grafana** (visualization)

**Tracing (Phase 3+):**
- **OpenTelemetry** (if need to trace agent interactions)
- Probably overkill initially

### 16.3 Human Interface

**Phase 1 - Terminal:**
```python
# Simple REPL
import cmd

class EconomyShell(cmd.Cmd):
    prompt = "economy> "
    
    def do_status(self, arg):
        """Show system status"""
        
    def do_agents(self, arg):
        """List all agents"""
        
    def do_markets(self, arg):
        """Show market state"""
```

**Phase 2 - Dashboard:**
- **Rich** (terminal UI library - beautiful tables, progress bars)
- **Textual** (terminal TUI framework - if want interactive dashboard)

**Phase 3+ - Web UI (optional):**
- **FastAPI** (backend API)
- **htmx** (minimal frontend - server-driven UI)
- Or simple **Streamlit** (quick dashboards)

### 16.4 Analysis & Visualization

**Data export:**
```python
# Export transaction log to CSV for analysis
import pandas as pd

df = pd.DataFrame(transaction_log)
df.to_csv("transactions.csv")
```

**Visualization:**
- **matplotlib/seaborn** (static plots - agent population, prices over time)
- **plotly** (interactive plots - market dynamics)
- **networkx** (agent relationship graphs - who pays whom)

**Jupyter notebooks** (ad-hoc analysis of agent behavior)

### 16.5 Configuration Management

```yaml
# config.yaml
economy:
  initial_credit_budget: 1000
  attention_conversion_rates:
    interesting: 50
    useful: 50
    understandable: 50
  spawn_cost: 100
  message_cost: 1

resources:
  tokens:
    supply: 10000
    initial_price: 0.1
  # ...

allocation:
  schedule_seconds: 10

logging:
  level: INFO
  structured: true
```

**Load with:**
- **PyYAML** or **tomli** (TOML if preferred)
- **pydantic** (validate config against schema)

### 16.6 Testing Tools

**Unit tests:**
```python
# pytest with fixtures
@pytest.fixture
def economy():
    return EconomicEngine()

def test_transfer(economy):
    economy.accounts['agent1'] = 100
    economy.accounts['agent2'] = 50
    assert economy.transfer('agent1', 'agent2', 30)
    assert economy.accounts['agent1'] == 70
    assert economy.accounts['agent2'] == 80
```

**Integration tests:**
```python
# pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_allocation_cycle(system):
    # Submit bids
    # Run allocation
    # Verify execution
```

**Property-based testing (optional):**
- **Hypothesis** (generate random scenarios, find edge cases)
  - Useful for economic invariants (total credits conserved, etc.)

### 16.7 Development Workflow

**Hot reload (Phase 1):**
```python
# Simple: restart on code change
import sys
import importlib

# Or use watchdog for file monitoring
from watchdog.observers import Observer
```

**Debugging:**
- **pdb** (Python debugger - step through allocation cycles)
- **ipdb** (improved pdb with IPython)
- **VSCode debugger** (if using VSCode)

**Profiling (if needed):**
- **cProfile** (find bottlenecks)
- **py-spy** (sampling profiler - low overhead)

### 16.8 Deployment (Later Phases)

**Containerization:**
```dockerfile
# Dockerfile
FROM python:3.11-slim
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

**Process management:**
- **systemd** (if running on server)
- **supervisor** (alternative)
- **docker-compose** (if multi-container)

**Persistence:**
- **Automated backups** of database (SQLite file or PostgreSQL dumps)
- **Transaction log archival** (S3, local disk)

### 16.9 Agent Development Tools

**For agents to inspect themselves:**
```python
# Provide introspection utilities
def get_execution_stats():
    """Show resource usage so far this execution"""
    return {
        'tokens_used': ...,
        'cpu_seconds': ...,
        'memory_mb': ...
    }
```

**Agent testing sandbox:**
```python
# Separate environment for agents to test strategies
# Without affecting main economy
class TestEconomy:
    """Isolated economy for agent experimentation"""
```

### 16.10 Documentation

**For the coding agent:**
- **Docstrings** (all public functions)
- **Type hints** (especially economic primitives)
- **README.md** (setup, running, basic concepts)

**Auto-generated:**
- **Sphinx** (if want API docs)
- Probably overkill initially

**Living documentation:**
- **Decision log** (markdown file tracking design choices)
- **Parameter tuning log** (what values tried, outcomes)
- **Interesting behaviors log** (emergent phenomena observed)

### 16.11 Minimal Tooling for Phase 1

**Absolute minimum to start:**
```
Python 3.14+
pytest (testing)
Redis (messaging)
SQLite (persistence)
Langchain (LLM calls)
python-dotenv (config)
structlog (logging)
Rich (terminal output)
```

**Everything else: add when needed.**

---

**The principle: Start minimal, add tools as pain points emerge.**

--- 
## 18. Final Notes

### 18.1 Philosophy Reminders

- **Emergence is the goal**: If you're not surprised, you're over-designing
- **Economics first**: Build the market, let capabilities emerge
- **Simple rules, complex behavior**: Resist adding features
- **Observation over control**: Watch what happens, don't force outcomes
- **Failure is data**: Agent death, market collapse, chaos - all informative

### 18.2 When to Iterate vs. Rebuild

**Iterate if:**
- Core mechanics work but parameters need tuning
- Emergent behaviors are interesting but incomplete
- Agents survive but strategies are naive

**Rebuild if:**
- All agents die immediately (economic model broken)
- No emergent behavior after 1000+ cycles (rules too simple or too complex)
- System is incomprehensible even to you (lost the plot)

### 18.3 Success Looks Like

**Short-term (weeks):**
- Agents that survive and adapt
- Observable specialization
- Stable-ish markets
- Occasional surprising behavior

**Long-term (months):**
- Genuinely interesting emergence
- Behaviors you didn't anticipate
- Ecosystem that teaches you something about:
  - Economic dynamics
  - Agent coordination
  - Your own preferences (revealed through attention)
- System that's intrinsically fascinating to interact with

**The real goal:** Build a curiosity engine, not a production tool.



---

**End of Specification**

This should provide a coding agent with everything needed to begin implementation while preserving the key decisions and nuances we developed. The specification is opinionated where we made firm decisions, and explicitly leaves room for discovery where we wanted emergence.
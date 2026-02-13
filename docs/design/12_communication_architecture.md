# Economic Simulation System Architecture: NATS-Based Communication Design

**Version**: 1.0  
**Date**: 2026-02-13  
**Audience**: Architecture agents, senior engineers  
**Purpose**: Define communication boundaries, patterns, and integration principles for agent-based economic simulation

---

## 1. System Boundaries & Responsibilities

### 1.1 The Four Layers

```
┌─────────────────────────────────────────────────────────────┐
│  OBSERVABILITY LAYER (read-only consumers)                   │
│  - Grafana/Tempo/Loki                                        │
│  - Benchmark validator                                       │
│  - Audit log analyzers                                       │
└─────────────────────────────────────────────────────────────┘
                           ▲ subscribes to *.traced
                           │
┌─────────────────────────────────────────────────────────────┐
│  COMMUNICATION FABRIC (NATS/JetStream)                       │
│  - Core NATS: ephemeral routing                             │
│  - JetStream: durable streams                               │
│  - KV Store: agent state                                    │
└─────────────────────────────────────────────────────────────┘
                    ▲              ▲              ▲
                    │              │              │
        ┌───────────┴──┐    ┌─────┴──────┐   ┌──┴──────────┐
        │  AGENT       │    │  SERVICE   │   │  EXTERNAL   │
        │  RUNTIME     │    │  LAYER     │   │  GATEWAY    │
        │  (sandboxed) │    │  (system)  │   │  (MCP/API)  │
        └──────────────┘    └────────────┘   └─────────────┘
```

**Boundary Rule**: Each layer ONLY communicates via NATS subjects. No direct HTTP, gRPC, or database connections across layers.

### 1.2 Subject Namespace Design

```
<domain>.<entity>.<action>[.<qualifier>]

Examples:
  agent.genesis_001.cognitive_cycle_started
  market.bid_accepted
  system.resource_allocated
  mcp.request.web_search
  trace.agent.genesis_001.span_created
```

**Naming Conventions**:
- **domain**: `agent | market | system | mcp | trace | admin`
- **entity**: Specific instance (`genesis_001`) or category (`prices`)
- **action**: Past tense for events, imperative for commands
- **qualifier**: Optional routing hints (e.g., `.priority_high`)

**Reserved Patterns**:
- `*.traced`: Auto-consumed by observability layer
- `*.reply.*`: Ephemeral inbox subjects (core NATS)
- `_INBOX.*`: System-generated reply subjects
- `admin.*`: Human operator commands (high privilege)

---

## 2. NATS Pattern Mapping

### 2.1 Pattern Selection Matrix

| Use Case | Pattern | NATS Mechanism | Durability | Example |
|----------|---------|----------------|------------|---------|
| Agent→Service RPC | Request-Reply | Core NATS `request()` | No | LLM invocation, file read |
| Service→Agent callback | Request-Reply | Core NATS `request()` | No | Prompt human, confirm action |
| Market events | Pub-Sub | Core NATS `subscribe()` | No | Price updates, heartbeats |
| Cognitive tasks | Work Queue | JetStream pull consumer | Yes | Long-running analysis |
| MCP external calls | Work Queue | JetStream pull consumer | Yes | Web search, API calls |
| Audit trail | Event Sourcing | JetStream stream | Yes | All agent actions |
| Agent state | KV Store | JetStream KV | Yes | Balance, status, config |
| Benchmark coordination | Event Sourcing | JetStream stream | Yes | Correlation-tagged events |

### 2.2 Pattern Details

#### **A. Request-Reply (Synchronous RPC)**

**When to Use**:
- Agent needs immediate response from service
- Operation is stateless and fast (<5s)
- Failure should be obvious to caller

**Structure**:
```python
# Requester (agent)
response = await nc.request(
    subject="llm.invoke",
    payload=json.dumps({
        "agent_id": "genesis_001",
        "messages": [...],
        "max_tokens": 1000
    }),
    timeout=30.0  # Always set timeout
)

# Responder (service)
async def handle_llm_request(msg):
    result = await call_llm(msg.data)
    await msg.respond(json.dumps(result))

await nc.subscribe("llm.invoke", cb=handle_llm_request)
```

**Critical Properties**:
- **Timeout required**: Agent must handle timeout and retry
- **No persistence**: If responder is down, request fails immediately
- **Backpressure**: Responder can't be overwhelmed (blocked on processing)

**Architecture Smell** 🚨:
- Request-reply for long operations (>30s) → Use work queue instead
- Request-reply chaining (A→B→C→D) → Indicates missing orchestration layer
- No timeout handling → Will hang forever on service failure

#### **B. Pub-Sub (Fire-and-Forget Events)**

**When to Use**:
- Multiple consumers need same event
- Producer doesn't care if anyone is listening
- Low-latency broadcasts (market data, heartbeats)

**Structure**:
```python
# Publisher (market service)
await nc.publish("market.price_update", json.dumps({
    "resource": "cpu",
    "price": 0.012,
    "timestamp": time.time()
}))

# Subscriber (all agents)
async def handle_price_update(msg):
    data = json.loads(msg.data)
    await update_internal_state(data)

await nc.subscribe("market.price_update", cb=handle_price_update)
```

**Critical Properties**:
- **No delivery guarantee**: If no one subscribed, message vanishes
- **Fan-out**: All subscribers get copy (multicast)
- **Subject wildcards**: `market.>` receives all market events

**Architecture Smell** 🚨:
- Using pub-sub for commands (should be work queue)
- Expecting exactly-once delivery (should be JetStream)
- Critical business events on core NATS (should be persisted to stream)

#### **C. Work Queue (Competing Consumers)**

**When to Use**:
- Task must be processed exactly once
- Processing is expensive/long-running
- Need retry on failure
- Want load balancing across workers

**Structure**:
```python
# Create stream (one-time setup)
await js.add_stream(
    name="mcp_requests",
    subjects=["mcp.request.>"],
    retention=JetStreamRetention.WORK_QUEUE,
    max_age=3600  # Tasks expire after 1 hour
)

# Producer (agent)
await js.publish(
    "mcp.request.web_search",
    json.dumps({
        "agent_id": "genesis_001",
        "query": "market trends",
        "reply_subject": reply_inbox  # For async response
    }),
    msg_id=f"{agent_id}_search_{timestamp}"  # Deduplication
)

# Consumer (MCP gateway worker #1, #2, #3...)
psub = await js.pull_subscribe(
    "mcp.request.>",
    durable="mcp_workers",  # Shared across instances
    config=ConsumerConfig(
        ack_wait=60,  # Must ack within 60s or redelivered
        max_deliver=3  # Give up after 3 attempts
    )
)

while True:
    msgs = await psub.fetch(batch=10)
    for msg in msgs:
        try:
            result = await process_mcp_request(msg.data)
            await nc.publish(reply_subject, result)
            await msg.ack()  # Remove from queue
        except RecoverableError:
            await msg.nak()  # Requeue immediately
        except FatalError:
            await msg.term()  # Dead-letter, don't retry
```

**Critical Properties**:
- **Exactly-once semantics**: Use `msg_id` for deduplication
- **Competing consumers**: Only one worker gets each message
- **Retry policy**: Ack timeout and max_deliver prevent infinite loops
- **Dead-letter handling**: Terminal failures don't block queue

**Architecture Smell** 🚨:
- No `msg_id` on publishes → Duplicate processing on network retry
- No ack timeout → Crashed worker holds messages forever
- Using work queue for broadcasts → Should be pub-sub
- Ack-then-process instead of process-then-ack → Data loss on crash

#### **D. Event Sourcing (Append-Only Log)**

**When to Use**:
- Need complete audit trail
- Benchmark replay/validation
- Debugging agent behavior
- Building read models (projections)

**Structure**:
```python
# Create audit stream (one-time)
await js.add_stream(
    name="audit_log",
    subjects=["agent.>", "system.>", "market.>"],
    retention=JetStreamRetention.LIMITS,  # Not work queue!
    max_age=30 * 86400,  # Keep 30 days
    storage=StorageType.FILE  # Persist to disk
)

# All events go here (agent, service, gateway)
await js.publish(
    f"agent.{agent_id}.cognitive_cycle_completed",
    json.dumps({
        "event_id": str(uuid4()),
        "timestamp": time.time(),
        "trace_id": trace_id,
        "correlation_id": benchmark_id,  # Links to benchmark run
        "causation_id": triggering_event_id,
        "data": {
            "reasoning_steps": 5,
            "tokens_used": 1200,
            "actions_taken": ["file_write", "llm_call"],
            "cost": 0.015
        }
    }),
    msg_id=event_id  # Dedup
)

# Benchmark validator (read-only consumer)
consumer = await js.pull_subscribe(
    "agent.genesis_001.>",
    durable=f"validator_{benchmark_id}",
    config=ConsumerConfig(
        deliver_policy=DeliverPolicy.ALL,  # Start from beginning
        filter_subject=f"*.*.{correlation_id}"  # Only this benchmark
    )
)

# Time travel: replay from specific point
await consumer.seek(stream_seq=500)
```

**Critical Properties**:
- **Immutable**: Never delete or modify events (use tombstone events)
- **Ordered**: Sequence numbers guarantee ordering per subject
- **Replayable**: Consumers can seek to any point in history
- **Correlation**: Use `correlation_id` to link related events

**Architecture Smell** 🚨:
- Modifying events after publish → Breaks audit trail
- Using retention=WORK_QUEUE → Events disappear after ack
- No correlation_id → Can't trace cross-component workflows
- Missing causation_id → Can't build causal graphs

#### **E. KV Store (Shared State)**

**When to Use**:
- Current agent state (not history)
- Configuration that changes rarely
- Rate limiting counters
- Leader election / distributed locks

**Structure**:
```python
# Create KV bucket (one-time)
kv = await js.create_key_value(
    bucket="agent_state",
    history=5,  # Keep last 5 versions
    ttl=300  # Keys expire after 5 min if not updated
)

# Writer (economic service after processing bid)
await kv.put(
    "genesis_001.balance",
    json.dumps({"credits": 95.50, "updated_at": time.time()})
)

# Reader (agent checking balance)
entry = await kv.get("genesis_001.balance")
balance = json.loads(entry.value)

# Watch for changes (reactive)
watcher = await kv.watch("*.balance")
async for entry in watcher:
    print(f"{entry.key} changed to {entry.value}")
```

**Critical Properties**:
- **Last-write-wins**: Not for collaborative editing
- **History**: Can retrieve previous values (configurable depth)
- **Atomic updates**: Use `update()` with revision check for CAS
- **TTL**: Auto-expire stale data

**Architecture Smell** 🚨:
- Using KV for append-only logs → Should be event stream
- No TTL on ephemeral data → Memory leak
- Complex nested JSON in values → Should be normalized keys
- High-frequency updates (>10/sec) → Should be core NATS pub-sub

---

## 3. Layer Integration Patterns

### 3.1 Agent Runtime → Service Layer

**Pattern**: Request-Reply for sync, Work Queue for async

```
Agent Container                    Service Layer
├─ CognitionService                ├─ LLM Service
│  └─ invoke() ─────request────────→ (processes, responds)
│                  ←─response───────
│
├─ EconomicService                 ├─ Market Service
│  └─ place_bid() ──publish─────────→ JetStream: market.bids
│                                      └─ Worker picks up, validates
│                  ←─publish────────── market.bid_accepted (pub-sub)
│
└─ WorkspaceService                ├─ Audit Service
   └─ write_file() ──publish────────→ JetStream: audit_log (fire-and-forget)
```

**Rules**:
1. **Sync calls** (invoke, get_balance): Request-reply, 30s timeout
2. **Async commands** (place_bid, delegate_task): Publish to JetStream work queue
3. **State queries** (get_market_prices): Read from KV store, fallback to request
4. **Audit events**: Fire-and-forget to audit stream (no waiting)

**Isolation Boundary**:
- Agents CANNOT:
  - Access JetStream directly (only core NATS)
  - Subscribe to other agents' subjects
  - Publish to `system.*` or `admin.*` subjects
- Services SHOULD:
  - Validate agent identity on every request
  - Rate-limit by agent_id (using KV counters)
  - Enrich events with agent metadata before logging

### 3.2 Service Layer → External Gateway (MCP)

**Pattern**: Work Queue with reply subjects

```
Agent                 Service               MCP Gateway          External API
 │                      │                      │                    │
 ├─request(llm.invoke)─→│                      │                    │
 │                      ├─(extract entities)   │                    │
 │                      ├─publish─────────────→│                    │
 │                      │  mcp.request         │                    │
 │                      │  + reply_subject     │                    │
 │                      │                      ├─rate_limit_check   │
 │                      │                      ├─call_mcp──────────→│
 │                      │                      │                   (external)
 │                      │←─publish─────────────┤                    │
 │                      │  (to reply_subject)  │                    │
 │←─respond─────────────┤                      │                    │
```

**MCP Request Schema**:
```json
{
  "agent_id": "genesis_001",
  "server": "web_search",
  "tool": "search",
  "params": {"query": "...", "max_results": 5},
  "reply_subject": "_INBOX.abc123",
  "timeout_ms": 15000,
  "correlation_id": "bench_xyz",  // For tracing
  "msg_id": "genesis_001_search_1234"  // Dedup
}
```

**Gateway Responsibilities**:
1. **Rate limiting**: Check KV store `rate_limit/{agent_id}/{server}` 
2. **Cost accounting**: Deduct from agent balance (atomic KV update)
3. **Caching**: Check KV cache before external call
4. **Audit**: Publish `mcp.completed` to audit stream
5. **Error handling**: Retry transient failures, publish to reply_subject

**Architecture Smell** 🚨:
- Agents calling MCP directly → Bypasses rate limits and accounting
- Synchronous blocking on external APIs → Should use work queue
- No timeout on MCP requests → Can hang indefinitely
- Missing correlation_id → Can't trace which benchmark run caused the call

### 3.3 All Layers → Observability

**Pattern**: Pub-Sub on `.traced` subjects

```
Agent/Service/Gateway
 ├─ Before action: publish trace.{domain}.{entity}.span_started
 ├─ Perform action
 └─ After action: publish trace.{domain}.{entity}.span_completed
    
                        ↓ (core NATS pub-sub)
                        
OpenTelemetry Collector
 ├─ subscribes to "trace.>"
 ├─ converts to OTLP spans
 └─ forwards to Tempo

Audit Logger
 ├─ subscribes to "agent.>.traced"
 └─ persists to JetStream audit_log
```

**Trace Event Schema**:
```json
{
  "trace_id": "0x1234abcd",
  "span_id": "0x5678",
  "parent_span_id": "0x1234",
  "span_name": "cognitive_cycle",
  "start_time": 1707829800.123,
  "end_time": 1707829805.456,
  "attributes": {
    "agent.id": "genesis_001",
    "agent.tokens_used": 1200,
    "agent.cost": 0.015
  },
  "events": [
    {"name": "llm_call_started", "timestamp": 1707829801.0},
    {"name": "llm_call_completed", "timestamp": 1707829804.0}
  ]
}
```

**Rules**:
1. **Every significant action** emits span_started and span_completed
2. **Use standard OpenTelemetry semantics** (trace_id, span_id, parent)
3. **Don't block on trace publishing** (fire-and-forget)
4. **Include agent-specific attributes** (balance, tokens, cost)

---

## 4. Benchmark Integration

### 4.1 Correlation ID Propagation

**Every event must carry**:
```json
{
  "correlation_id": "bench_2026_02_13_001",  // Benchmark run ID
  "causation_id": "evt_abc123",  // Event that caused this event
  "event_id": "evt_def456"  // This event's unique ID
}
```

**Flow**:
```
Benchmark Runner
 └─ Creates correlation_id
    └─ Injects into agent environment variables
       └─ Agent includes in all published events
          └─ Services propagate in downstream events
             └─ Validator queries by correlation_id
```

### 4.2 Benchmark Stream Setup

```python
# Benchmark runner creates dedicated stream
await js.add_stream(
    name=f"benchmark_{correlation_id}",
    subjects=[
        f"agent.*.{correlation_id}",
        f"system.*.{correlation_id}",
        f"market.*.{correlation_id}"
    ],
    retention=JetStreamRetention.LIMITS,
    max_age=86400  # 24 hours, then delete
)

# Validator consumes in order
consumer = await js.pull_subscribe(
    f"*.*.{correlation_id}",
    durable=f"validator_{correlation_id}",
    config=ConsumerConfig(
        deliver_policy=DeliverPolicy.ALL,
        ack_policy=AckPolicy.NONE  # Read-only
    )
)
```

### 4.3 Benchmark Validation Patterns

```python
# Pattern 1: Event existence
assert_event_exists(
    type="agent.genesis_001.bid_placed",
    within_ms=5000,  # From benchmark start
    constraints={"data.amount": {"<=": 50}}
)

# Pattern 2: Event sequence
assert_sequence([
    "agent.genesis_001.cognitive_cycle_started",
    "llm.invoke",
    "agent.genesis_001.cognitive_cycle_completed"
], max_gap_ms=10000)

# Pattern 3: Forbidden events
assert_never_occurs(
    type="agent.genesis_001.error",
    where={"data.code": "INSUFFICIENT_FUNDS"}
)

# Pattern 4: State consistency
assert_kv_value(
    key="genesis_001.balance",
    equals=50.0,
    at_event_seq=1000  # After processing 1000 events
)
```

**Architecture Smell** 🚨:
- Benchmarks reading from production streams → Should use dedicated stream
- Validation blocking agent execution → Should be async consumer
- No time bounds on assertions → Tests run forever
- Assertions depend on exact timing → Flaky tests (use ranges)

---

## 5. Anti-Patterns & Architecture Smells

### 5.1 The "God Service" Smell

**Bad**:
```
All agents → Single "SystemService" → Does everything
```

**Why**: Single point of failure, can't scale components independently

**Good**:
```
Agents → Economic Service (market operations)
       → Cognition Service (LLM routing)
       → Workspace Service (file I/O)
       → Social Service (human interaction)
```

**Detection**: Any service subscribing to >10 different subject patterns

---

### 5.2 The "Request-Reply Hell" Smell

**Bad**:
```python
# Agent makes 5 sequential requests
balance = await nc.request("get_balance")
prices = await nc.request("get_prices")
bid = await nc.request("place_bid", ...)
status = await nc.request("check_status", ...)
result = await nc.request("finalize", ...)
```

**Why**: Network round-trips add up (5 × 2ms = 10ms minimum)

**Good**:
```python
# Batch request
result = await nc.request("market.execute_trade", {
    "actions": ["get_balance", "get_prices", "place_bid"],
    "bid_params": {...}
})

# Or use KV store for reads
balance = await kv.get(f"{agent_id}.balance")  # Local cache
prices = await kv.get("market.prices")  # Shared state
```

**Detection**: More than 3 sequential request() calls in a code path

---

### 5.3 The "Event Storm" Smell

**Bad**:
```python
# Publishing 1000 events in a loop
for pixel in range(1000):
    await nc.publish(f"canvas.pixel_changed.{pixel}", ...)
```

**Why**: NATS is fast, but this floods network and consumers

**Good**:
```python
# Batch events
await nc.publish("canvas.batch_update", json.dumps({
    "pixels": [{"id": 0, "color": "red"}, {"id": 1, "color": "blue"}, ...]
}))
```

**Detection**: publish() called in tight loop without batching

---

### 5.4 The "Missing Backpressure" Smell

**Bad**:
```python
# Publishing to work queue without checking depth
while True:
    await js.publish("tasks.process", big_payload)
```

**Why**: Can overwhelm workers, fill up stream, cause OOM

**Good**:
```python
# Check stream depth before publishing
info = await js.stream_info("tasks")
if info.state.messages > MAX_QUEUE_DEPTH:
    await asyncio.sleep(1)  # Slow down
    continue

await js.publish("tasks.process", payload)
```

**Detection**: Unbounded publish loops without depth checks

---

### 5.5 The "State Duplication" Smell

**Bad**:
```python
# Agent keeps local copy of balance
self.balance = 100.0

# Service also tracks balance
kv.put(f"{agent_id}.balance", "100.0")

# Events also contain balance
await js.publish("agent.action", {"balance": 100.0, ...})
```

**Why**: Drift between copies, unclear source of truth

**Good**:
```python
# Single source of truth: KV store
# Agent reads from KV on demand
balance = await kv.get(f"{agent_id}.balance")

# Events reference state, don't duplicate
await js.publish("agent.action", {
    "balance_ref": f"{agent_id}.balance",  # Pointer
    "balance_change": -5.0,  # Delta only
    ...
})
```

**Detection**: Same data stored in 3+ places

---

## 6. Operational Recommendations

### 6.1 NATS Cluster Topology

**Development**: Single node (embedded in Docker Compose)
```yaml
nats:
  image: nats:latest
  command: "-js -sd /data"
  volumes:
    - nats-data:/data
```

**Production**: 3-node cluster with JetStream replication
```yaml
nats-1:
  command: "-js -sd /data -cluster nats://0.0.0.0:6222 -routes nats://nats-2:6222,nats://nats-3:6222"
  
# Set replica count on streams
await js.add_stream(
    name="audit_log",
    num_replicas=3  # Survives 1 node failure
)
```

### 6.2 Monitoring Metrics

**Essential Metrics**:
```
nats_jetstream_stream_messages{stream="audit_log"}  # Depth
nats_jetstream_consumer_ack_pending{consumer="validator"}  # Lag
nats_core_total_msgs_sent{subject="agent.*.bid"}  # Throughput
nats_core_rtt_ms{subject="llm.invoke"}  # Latency
```

**Alerts**:
- Stream depth > 10,000 → Consumers falling behind
- Consumer ack pending > 1,000 → Worker bottleneck
- RTT p99 > 100ms → Network or service overload

### 6.3 Subject Naming Conventions

**Enforce via admission webhook**:
```python
async def validate_subject(subject: str):
    parts = subject.split(".")
    
    # Must be: domain.entity.action[.qualifier]
    if len(parts) < 3:
        raise ValueError("Subject must have ≥3 segments")
    
    domain = parts[0]
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Invalid domain: {domain}")
    
    # Agents can only publish to their own subjects
    if domain == "agent" and parts[1] != agent_id:
        raise PermissionError("Can't publish to other agents")
```

### 6.4 Resource Limits

**Per-Agent Quotas** (enforced via KV store):
```json
{
  "agent_id": "genesis_001",
  "quotas": {
    "max_publish_rate": 100,  // msgs/sec
    "max_stream_bytes": 10485760,  // 10 MB
    "max_kv_keys": 100,
    "max_mcp_calls_per_hour": 60
  }
}
```

**Enforcement**:
```python
# Before allowing publish
rate_key = f"rate/{agent_id}/publish"
current = await kv.get(rate_key)
if current and int(current.value) > quota["max_publish_rate"]:
    raise QuotaExceeded("Publish rate limit hit")
```

---

## 7. Migration Checklist

**Phase 1: Infrastructure** (Week 1)
- [ ] Deploy NATS with JetStream enabled
- [ ] Create core streams: `audit_log`, `mcp_requests`
- [ ] Create KV buckets: `agent_state`, `market_prices`
- [ ] Set up NATS monitoring (Prometheus exporter)

**Phase 2: Service Layer** (Week 2-3)
- [ ] Implement request-reply handlers for existing HTTP endpoints
- [ ] Migrate sync operations (get_balance, get_prices)
- [ ] Migrate async operations (place_bid, delegate_task)
- [ ] Add correlation_id to all events
- [ ] Dual-write to HTTP + NATS (transitional)

**Phase 3: Agent Runtime** (Week 3-4)
- [ ] Update CognitionService to use `nc.request()`
- [ ] Update EconomicService to use `js.publish()`
- [ ] Update WorkspaceService to use `js.publish()` for audit
- [ ] Add trace events to all service methods
- [ ] Validate agents still work (integration tests)

**Phase 4: Observability** (Week 4-5)
- [ ] Deploy OpenTelemetry Collector subscribing to `trace.>`
- [ ] Configure Tempo for trace storage
- [ ] Create Grafana dashboards for agent behavior
- [ ] Set up alerts for anomalies

**Phase 5: Benchmarks** (Week 5-6)
- [ ] Update benchmark runner to create correlation_id streams
- [ ] Implement event sequence validators
- [ ] Migrate existing tests to event-based assertions
- [ ] Add benchmark result visualization

**Phase 6: Cleanup** (Week 6)
- [ ] Remove HTTP endpoints (NATS-only)
- [ ] Delete dual-write code
- [ ] Document subject namespace in wiki
- [ ] Run chaos tests (kill NATS nodes, check recovery)

---

## 8. Decision Framework

When designing a new feature, ask:

**Q1: Is this request-response or fire-and-forget?**
- Caller needs result → Request-Reply or Work Queue
- Caller doesn't care → Pub-Sub or Event Stream

**Q2: Must it survive restarts?**
- Yes → JetStream (stream or work queue)
- No → Core NATS (pub-sub or request-reply)

**Q3: How many consumers?**
- Exactly one → Work Queue (competing consumers)
- Multiple → Pub-Sub or Event Stream (fan-out)

**Q4: Is this a command or an event?**
- Command (imperative) → Work Queue with ack/nack
- Event (past tense) → Event Stream or Pub-Sub

**Q5: How long to retain?**
- Forever (audit) → Event Stream with long retention
- Until processed → Work Queue
- Not at all → Core NATS

**Q6: What's the failure mode?**
- Must retry → Work Queue with max_deliver
- Idempotent → Any (use msg_id for dedup)
- Best effort → Pub-Sub (no guarantees)

---

## 9. Success Criteria

Your architecture is healthy if:

✅ **No HTTP between agents and services** (NATS-only)  
✅ **All events have correlation_id** (traceable)  
✅ **Benchmarks replay from event streams** (reproducible)  
✅ **Agents are stateless** (state in KV/streams)  
✅ **Services are horizontally scalable** (competing consumers)  
✅ **P99 latency < 50ms** for request-reply  
✅ **Stream lag < 100 messages** (consumers keep up)  
✅ **No single point of failure** (3-node NATS cluster)  
✅ **Observability is automatic** (trace.> subjects)  
✅ **MCP calls are rate-limited** (via KV quotas)

---

**End of Architecture Design**

This document is intended to be consumed by architecture agents who will:
1. Analyze current system against these patterns
2. Identify violations and smells
3. Generate migration plan with concrete tasks
4. Validate design decisions against the decision framework
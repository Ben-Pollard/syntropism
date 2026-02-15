# Persistence & Messaging Roles

To clarify the confusion around persistence, here is the breakdown of how the different components interact and why they are all necessary for the target architecture.

## 1. The Database (PostgreSQL/SQLite)
- **Role**: **System State (Source of Truth)**.
- **What it stores**: Agent balances, transaction ledgers, market prices, resource allocation records.
- **Why we need it**: It provides ACID guarantees for economic transactions. If the system restarts, the DB ensures Agent A still has exactly 50.5 credits.
- **Analogy**: The bank's ledger.

## 2. OTel Sinks (Arize Phoenix)
- **Role**: **Behavioral Telemetry (Diagnostic Layer)**.
- **What it stores**: Traces, spans, logs, LLM prompts/responses, tool call metadata.
- **Why we need it**: It answers "Why did the agent do that?". It allows us to visualize the reasoning chain and run "Evals" (LLM-as-a-Judge) to score performance. It is **not** used for system logic, only for observation and evaluation.
- **Analogy**: The security camera footage and black box recorder.

## 3. NATS JetStream
- **Role**: **Durable Messaging & Event Sourcing (The Glue)**.
- **What it gives us in addition**:
    - **Durable Event Log**: Unlike standard NATS (which is fire-and-forget), JetStream saves messages to disk. This allows the **Benchmark Runner** to "time travel" and replay events to verify if an agent followed the correct sequence.
    - **Work Queues**: Ensures that expensive tasks (like MCP tool calls) are processed **exactly once**. If a worker crashes mid-task, JetStream redelivers it to another worker.
    - **KV Store**: Provides a way for agents to "watch" state changes (like price updates) reactively without polling a database.
- **Do we need it right now?**: 
    - For simple request-reply? **No.** 
    - For the **Benchmark Runner** and **MCP Gateway**? **Yes.** 
    - Since your goal is to get the "eval/debugging platform" up, JetStream is the foundation that allows the Benchmark Runner to function.

## Summary Table

| Component | Primary Purpose | Persistence Type | Key Feature |
| --- | --- | --- | --- |
| **Database** | Economic Integrity | Relational / ACID | Transactions & Balances |
| **Phoenix** | Debugging & Eval | Trace / Document | Reasoning Visualization |
| **JetStream** | Coordination | Append-only Log | Replay & Work Queues |

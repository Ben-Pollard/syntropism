# Current Architecture

## Overview
The Syntropism system is an agent-based economic simulation where agents compete for scarce resources (CPU, Memory, Tokens, Attention) using a credit-based currency. The system is designed to be event-driven, using NATS for inter-service communication and OpenTelemetry for observability.

## Resource Definitions & Scarcity
Resources are defined by their availability over time, adhering to the "Physics of Scarcity":
- **Time-Based Allocation**: Resources are priced and allocated per unit time (e.g., % of max capacity for a specific duration).
- **LLM Scarcity**: LLM utilization is capped by a system-wide maximum spend per unit time, treating commercial API costs as a finite physical resource.
- **Attention**: A finite resource representing human or system focus, priced and allocated alongside compute.

## System Components

### 1. Economic Engine (`syntropism/domain/economy.py`)
Manages the credit ledger, agent balances, and transactions.
- **Responsibilities**: Credit transfers, balance queries, transaction history.
- **Invariants**: Conservation of credits (except for human rewards and resource burning).

### 2. Market Manager (`syntropism/domain/market.py`)
Handles resource pricing and market state.
- **Responsibilities**: Dynamic price updates based on utilization, providing market state via NATS.
- **Pricing Logic**: Simple linear adjustment based on high/low utilization thresholds.

### 3. Allocation Scheduler (`syntropism/core/scheduler.py`)
Coordinates resource allocation through a bidding process.
- **Responsibilities**: Processing bids, sorting by price, allocating resources based on supply, updating market utilization.
- **Mechanism**: Highest-bidder-first allocation within supply constraints.

### 4. Benchmark Runner (`syntropism/benchmarks/runner.py`)
Evaluates agent performance against predefined scenarios.
- **Responsibilities**: Collecting events from NATS, validating event sequences against scenario requirements.
- **Status**: Currently lacks full integration with the event taxonomy defined in design docs.

## Data Flow & Interaction

```mermaid
graph TD
    Agent[Agent] -->|Place Bid| Market[Market Manager]
    Market -->|Forward Bid| Scheduler[Allocation Scheduler]
    Scheduler -->|Check Balance| Economy[Economic Engine]
    Scheduler -->|Allocate| Execution[Execution Context]
    Execution -->|Emit Events| NATS[NATS Event Bus]
    Benchmark[Benchmark Runner] -->|Subscribe| NATS
    Economy -->|Update Balance| DB[(Database)]
    Market -->|Update Prices| DB
    Scheduler -->|Record Execution| DB
```

## Observability Stack

The system utilizes an **OpenInference-based observability stack** centered around **Arize Phoenix** to treat LLM agents as distributed systems. This enables "Behavioral Tracing" rather than just infrastructure monitoring.

### 1. Behavioral Tracing Architecture
Reasoning traces and tool calls are captured as first-class citizens using OpenInference semantic conventions.

```mermaid
graph TD
    subgraph "Agent Runtime"
        Agent[Agent Logic]
        OI_Inst[OpenInference Instrumentation]
        Reasoning[Reasoning Engine]
    end

    subgraph "Observability Pipeline"
        OTel[OTel Collector]
        Phoenix[Arize Phoenix]
    end

    Agent --> OI_Inst
    Reasoning -->|llm.input_messages| OI_Inst
    Reasoning -->|llm.output_messages| OI_Inst
    OI_Inst -->|OTLP/HTTP| OTel
    OTel -->|Export| Phoenix

    subgraph "Evaluation & Benchmarking"
        Phoenix -->|Promote to Dataset| Evals[Phoenix Evals]
    end
```

### 2. Trace Propagation via NATS
To maintain trace continuity across the asynchronous NATS bus, the system implements W3C Trace Context propagation.

```mermaid
sequenceDiagram
    participant A as Agent
    participant S as Service Layer
    participant N as NATS Bus
    participant E as Economic Engine
    participant P as Arize Phoenix

    A->>S: Request Balance
    S->>S: Inject traceparent into Header
    S->>N: Publish (with Header)
    N->>E: Deliver Message
    E->>E: Extract traceparent
    E->>E: Start Child Span
    E-->>P: Export Span
    E->>N: Respond
    N->>S: Deliver Response
    S->>A: Return Result
```

### 3. Components
| Component | Technology | Role |
| --- | --- | --- |
| **Instrumentation** | `openinference-instrumentation` | Wraps agents/LLMs to emit structured spans (prompts, tool calls). |
| **Transport** | **OpenTelemetry (OTel)** | The pipe carrying data from NATS agents to the backend. |
| **Collector** | `otel-collector` | Aggregates and routes traces to Phoenix. |
| **Trace Backend** | **Arize Phoenix** | Visualization, embedding analysis, and evaluation. |

## Event Flow (Target)

```mermaid
sequenceDiagram
    participant A as Agent
    participant S as Scheduler
    participant E as Economy
    participant M as Market
    participant B as Benchmark Runner

    A->>M: Place Bid
    M->>S: Process Bid
    S->>E: Deduct Credits
    E-->>B: Emit credits_transferred (Burn)
    S->>S: Allocate Resources
    S-->>B: Emit resources_allocated
    S->>M: Update Utilization
    M-->>B: Emit price_update
```

## Current Misalignments

### 1. Event Emission
- **Design**: `docs/design/10_agent_benchmark.md` specifies a rich taxonomy of events (`bid_placed`, `resources_allocated`, `price_update`, etc.).
- **Implementation**: Current code has minimal event emission. `BenchmarkRunner` listens to `benchmark_events` but the core logic (Scheduler, Economy, Market) does not yet emit these specific events to NATS.

### 2. Resource Pricing
- **Design**: `docs/design/03_market.md` calls for "Physics of Scarcity" and "Supply and Demand Dynamics".
- **Implementation**: `MarketManager` uses a basic threshold-based price adjustment. It lacks the sophisticated supply/demand curves and "Attention" pricing described in the design.

### 3. Credit Flow
- **Design**: `docs/design/02_money.md` specifies that credits spent on resources should be **Burned**.
- **Implementation**: `AllocationScheduler` deducts credits from the agent balance. While not explicitly transferred to a "burn" account, the credits are removed from the agent's balance, effectively removing them from the active agent economy.

### 4. Benchmark Data
- **Status**: Benchmark data files (e.g., `er001.json`) are currently empty or minimal. They need to be populated with the `required_event_sequence` matching the taxonomy in `10_agent_benchmark.md`.

### 5. Observability Instrumentation
- **Design**: `docs/design/14_observability.md` specifies an OpenInference-based stack with Arize Phoenix.
- **Implementation**:
    - Infrastructure (NATS, OTel Collector, Phoenix) is deployed via Docker Compose.
    - `EconomicEngine` has basic manual OTel instrumentation.
    - **Gap**: Missing `openinference-instrumentation` for LLM-specific attributes.
    - **Gap**: `ReasoningTrace` events are emitted to NATS but not yet integrated as OTel span attributes/events.
    - **Gap**: NATS header propagation for `traceparent` is not yet implemented in the service layer.

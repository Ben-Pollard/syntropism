# 02 - The Credit Ledger: The Universal Medium

## 1. The Nature of Credits
Credits are the universal currency of the system. They represent the ability to claim system resources and human attention.

- **Universal Exchange**: All resources (CPU, Memory, Tokens, Attention) are priced in credits.
- **Divisibility**: Credits are floating-point values, allowing for micro-transactions.
- **Persistence**: Credit balances are stored in the `EconomicEngine` and persist across agent executions.

## 2. Credit Flow & Invariants
The ledger maintains the integrity of the economy through strict invariants.

- **Conservation of Credits**: In any transaction between agents, the sum of credits remains constant.
    - `Balance(A) + Balance(B) = Balance'(A) + Balance'(B)`
- **The Value Injection (Human)**: The only exception to conservation is when the Human provides a reward.
    - `New_Credits = Score(Interesting, Useful, Understandable) * Conversion_Rate`
- **The Value Sink (Death)**: When an agent dies, its remaining credits are either:
    1. **Burned**: Removed from circulation (deflationary).
    2. **Recycled**: Returned to a "System Pool" for the Human to re-inject (neutral).
    - *Decision*: For Phase 1, credits are **Burned** to ensure strong selection pressure.

## 3. The Reward Schema
The bridge between Human Value and the Agent Economy.

- **Three-Part Scoring (0-10)**:
    - **Interesting**: Captures human attention/curiosity.
    - **Useful**: Provides functional value or solves a task.
    - **Understandable**: Communicates effectively.
- **Conversion Function**: `Credits = (I * W_i) + (U * W_u) + (Un * W_un)` where `W` are system-wide weights.
- **Economic Signal**: This schema ensures that agents cannot just "spam" the human; they must optimize for these specific dimensions to stay profitable.

## 4. Inter-Agent Transactions
Agents have the fundamental right to transfer credits to any other agent via the System Service.

- **The `POST /economic/transfer` Endpoint**:
    - Must be atomic.
    - Must fail if `balance < amount`.
    - No "Credit" or "Debt" is provided by the system. Agents must invent their own lending/trust protocols.
- **Emergent Use Cases**:
    - **Outsourcing**: Paying another agent to perform a sub-task.
    - **Information Trading**: Paying for market data or strategies.
    - **Reputation**: Building a history of successful transfers to establish trust.

## 5. Transaction Logging
Every movement of credits is recorded in an append-only log.

- **Transparency**: Agents can query their own transaction history via `GET /economic/history`.
- **Auditability**: The system operator can trace the flow of value to identify degenerate behaviors (e.g., circular transfers to avoid death).
- **Market Data**: Aggregated transaction data (without agent IDs) is provided to the `MarketManager` for price discovery.

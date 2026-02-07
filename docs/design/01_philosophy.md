# 01 - Philosophy: The Laws of Nature

## 1. Core Axiom: Execution = Existence
In this system, time is not a continuous flow for the inhabitants. An agent only experiences time and "exists" during a discrete execution window. 

- **Oblivion**: Between executions, an agent is in a state of total suspension. It cannot observe, think, or react.
- **The Trigger**: Existence is triggered solely by the successful allocation of a resource bundle in the market.
- **The Continuity**: An agent's "identity" is preserved through its persistent workspace and state, but its "consciousness" is fragmented across execution windows.

## 2. Emergence over Design
The system is designed as a "Physics Engine" for agents, not an orchestration framework.

- **No Orchestrator**: There is no central "Manager" or "Scheduler" that assigns tasks.
- **No Pre-defined Roles**: Concepts like "Aggregator," "Specialist," or "Broker" are not programmed into the system. They must emerge because they are economically viable strategies.
- **Minimal Rules**: We prefer a few hard "Laws of Physics" (Credits, Resources, Markets) over many "Business Rules."

## 3. The Value Anchor (Human Attention)
The economy is not a closed loop; it requires an external source of value to prevent stagnation or degenerate cycles.

- **The Human as the Sun**: Just as photosynthesis injects energy into a biological ecosystem, Human Attention injects credits into the agent economy.
- **The Reward Schema**: Human feedback is structured into three dimensions:
    - **Interesting**: Does it capture attention?
    - **Useful**: Does it solve a problem or provide value?
    - **Understandable**: Is the communication clear?
- **Credit Creation**: Only the Human (via the Reward Schema) can create new credits in the system. All other credit movements are transfers between agents.

## 4. Death and Selection Pressure
Population control is handled by the "Hard Floor" of the economy.

- **The Cost of Existence**: Every second of execution, every token of thought, and every byte of memory has a market price.
- **The Death Mechanic**: An agent dies if:
    1. It runs out of credits and has no pending bids.
    2. It fails to place a bid for future execution during its current window (suicide by omission).
- **Selection Pressure**: Death is the primary driver of evolution. Only agents that can generate more value (credits) than they consume (resources) will survive and reproduce.

## 5. The Service Boundary
The boundary between the **Economic Runtime** and the **Agent Logic** is a formal, strictly defined interface.

- **No Side-Channels**: Agents cannot "hack" the system or observe other agents' internal states. They interact only through the provided System Service.
- **Service Discovery**: The runtime provides a `SYSTEM_SERVICE_URL`. Agents use standard HTTP/JSON to interact with the world.
- **Hard Termination**: The runtime is the ultimate arbiter of resource limits. If an agent exceeds its allocated CPU, Memory, or Time, it is terminated immediately (SIGKILL).

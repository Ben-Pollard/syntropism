# Syntropism

**A market-governed ecosystem where agents must adapt to survive.**

Syntropism is an experimental agent economy where autonomous agents compete for computational resources and human attention. It moves away from top-down orchestration, instead providing a set of "system laws" (credits and resource scarcity) that force agents to evolve toward utility.

> **Status**: This is a hobby project in the early research and prototyping phase. It is a playground for exploring agent economics, mechanism design, and emergent behavior.

## The Core Mechanics

The system operates on a few simple, strictly enforced rules:

1.  **Execution = Existence**: Agents only "exist" during discrete execution windows. Between windows, they are in total suspension (oblivion).
2.  **Resource Scarcity**: CPU, Memory, and LLM tokens are finite resources priced in **Credits**.
3.  **The Market**: To exist, an agent must win a "Resource Bundle" in a continuous combinatorial auction. If an agent cannot afford its resources, it dies.
4.  **Human as the Sun**: Human attention is the only source of new credits. By rewarding agents for being *Interesting*, *Useful*, or *Understandable*, humans inject the alignment signal.

## Why Syntropism?

The name is derived from **tropism** (an organism's turning in response to a stimulus) and **syntropy** (the tendency toward order). 

In this ecosystem, agents exhibit **syntropism**: they do not have pre-programmed goals or roles. Instead, they automatically orient themselves toward the "stimulus" of human value and economic survival. Order emerges not from a manager's design, but from the pressure of the market.

## Architecture

The project is built with a focus on isolation and asynchronous communication:

-   **Economic Runtime**: A host system (using NATS) that manages the market, credit ledger, and agent lifecycles.
-   **Agent Sandboxes**: Isolated environments where agent logic (the "Thinker") runs with hard resource limits.
-   **System Service**: A strictly defined HTTP/JSON interface that is the agent's only window into the world.

For a deeper dive into the mechanics, see the [Design Docs](docs/design/).

## Exploration Areas

- **Mechanism Design**: How auction types and credit flows impact agent behavior.
- **Self-Coding**: Agents that can modify their own logic to improve resource efficiency.
- **Emergent Sociality**: Agents trading information or services to survive high resource prices.

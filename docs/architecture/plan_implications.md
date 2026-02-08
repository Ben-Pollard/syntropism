# Plan Implications: bp-agents-2

This document identifies the technical debt, breaking changes, and infrastructure requirements introduced by the upcoming implementation plans, cross-referenced with the current architecture and recommendations.

## 1. Technical Debt

The following technical debt is introduced or reinforced by the current plans:

- **Monolithic Orchestrator**: The `MVS Implementation Plan` explicitly builds a monolithic `main.py`. While necessary for "Proof of Life," this reinforces the sequential execution model and delays the transition to an asynchronous, task-queue based architecture recommended in `recommendations.md`.
- **SQLite Persistence**: The MVS continues to use SQLite. This will become a bottleneck for concurrent access as soon as parallel execution is attempted, as noted in the scalability recommendations.
- **Tight Coupling in Service Layer**: The `Alignment Audit: Agent Runtime` plan adds endpoints directly to `bp_agents/service.py` that interact with the `AllocationScheduler`. This continues the pattern of mixing framework (FastAPI) with business logic, which contradicts the "Clean Architecture" recommendation.
- **Manual Bootstrap**: The system relies on a manual bootstrap of the Genesis Agent. This lacks a robust, automated system recovery or "cold start" procedure.
- **Hardcoded Economic Parameters**: While the `monolith_spec.md` mentions configuration, the implementation plans often refer to hardcoded values (e.g., `initial_credit_budget: 1000`). This increases the effort required for parameter tuning.

## 2. Breaking Changes

The transition to the "Pure Decoupling" architecture and MVS introduces several breaking changes:

- **Handshake Protocol**: The introduction of `env.json` as the primary handshake mechanism is a breaking change for any existing agent logic that might have relied on environment variables or direct API calls without an `execution_id`.
- **Resource Bundle Bidding**: The `MVS Implementation Plan` changes `POST /market/bid` to require a full resource bundle. Existing agents that bid for single resources will fail.
- **Attention Gating**: Agents can no longer call `POST /human/prompt` at will. They must have been allocated the "Attention" resource in their current `execution_id`.
- **Workspace Structure**: Moving to `workspaces/` in the project root and using `agent-{id}` subdirectories changes the filesystem layout for agents.
- **API Schema Updates**: New schemas for `MessageRequest` and `BidRequest` will break any existing clients not updated to the new Pydantic models.

## 3. New Infrastructure Requirements

The upcoming plans necessitate the following infrastructure additions:

- **Persistent Workspace Root**: A dedicated `workspaces/` directory on the host with appropriate permissions for Docker mounting.
- **Standardized Agent Runner Image**: A new `bp-agent-runner` Docker image (defined in `runtime/Dockerfile`) that includes Poetry and the necessary runtime dependencies.
- **Resource Metering**: The `AllocationScheduler` now requires logic to track and enforce `cpu_seconds`, `memory_mb`, and `tokens` consumption, which may require integration with Docker stats or per-request interceptors.
- **Terminal-Based Interaction Loop**: A new interactive loop in `main.py` to handle human scoring of agent prompts.
- **Network Policy Enforcement**: To meet security recommendations, the infrastructure must support strict Docker network policies to isolate agents from each other and the host.

## 4. Alignment with Recommendations

| Recommendation | Plan Status | Notes |
| :--- | :--- | :--- |
| **Asynchronous Execution** | ❌ Not Addressed | MVS remains monolithic/sequential. |
| **Database Scaling** | ❌ Not Addressed | Still using SQLite. |
| **Network Isolation** | ⚠️ Partial | Mentioned in spec, but implementation details are thin in MVS plan. |
| **API Authentication** | ✅ Addressed | `execution_id` validation in `POST /human/prompt` provides basic gating. |
| **Dependency Injection** | ❌ Not Addressed | Orchestrator still instantiates components directly. |
| **Automated Migrations** | ❌ Not Addressed | No mention of Alembic in implementation tasks. |
| **Pure Decoupling** | ✅ Strong Alignment | `env.json` and `workspaces/` implementation directly follows this goal. |

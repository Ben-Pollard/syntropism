# Architectural Recommendations: bp-agents-2

This document provides recommendations for the evolution of the `bp-agents-2` system, based on an evaluation of the current architecture against industry standards (SOLID, Clean Architecture, Twelve-Factor App) and Agent-Based System patterns.

## 1. Scalability

### Current State
The system is currently a monolith with a sequential execution loop. The `Orchestrator` runs agents one by one in a single process.

### Recommendations
- **Asynchronous Execution**: Transition from sequential execution to a task-queue based model (e.g., Celery, RabbitMQ, or Temporal). This allows multiple agents to run in parallel across different worker nodes.
- **Database Scaling**: Move from SQLite to a client-server database like PostgreSQL to support concurrent access from multiple worker nodes.
- **Stateless Orchestrator**: Ensure the orchestrator can be horizontally scaled by moving all state (including the "current cycle" status) into the database or a distributed cache (Redis).
- **Resource Metering Service**: Decouple resource tracking from the main database to handle high-frequency updates during agent execution.

## 2. Security

### Current State
Agents run in Docker containers with resource limits. Communication is via a FastAPI service.

### Recommendations
- **Network Isolation**: Implement strict Docker network policies. Agents should only be able to talk to the `SystemService` and not to each other or the host's internal network unless explicitly permitted.
- **API Authentication**: Implement per-agent API keys or JWTs for the `SystemService`. Currently, the `agent_id` is passed in the request body, which can be easily spoofed by a malicious agent.
- **Workspace Sanitization**: Implement stricter validation on workspace paths and file operations in `genesis.py` to prevent path traversal attacks.
- **Read-Only Root FS**: Run agent containers with a read-only root filesystem, only allowing writes to the designated `/workspace` volume.

## 3. Resilience

### Current State
The system uses a single loop. If the orchestrator crashes, the entire system stops. Agent failures are logged but don't trigger automatic retries or recovery.

### Recommendations
- **Process Supervision**: Use a process manager (like `systemd` or `supervisord`) or a container orchestrator (Kubernetes) to ensure the system services automatically restart on failure.
- **Idempotent Operations**: Ensure that the `AllocationCycle` and `Execution` steps are idempotent. If the system crashes mid-cycle, it should be able to resume without double-charging agents or skipping executions.
- **Circuit Breakers**: Implement circuit breakers for external dependencies (like LLM providers for token counting) to prevent a single failing service from bringing down the entire economy.
- **Dead Letter Queues**: For failed agent executions that are not due to resource exhaustion, move them to a "dead letter" state for manual inspection or automated debugging.

## 4. Maintainability

### Current State
The system follows a modular structure but has some tight coupling between business logic and database models (Active Record-like patterns).

### Recommendations
- **Dependency Injection**: Use a proper dependency injection framework or pattern. Currently, classes like `ExecutionSandbox` are instantiated directly inside `Orchestrator`, making unit testing difficult.
- **Repository Pattern**: Introduce a Repository layer to abstract database operations. This will decouple the business logic (Economy, Market) from SQLAlchemy models.
- **Domain-Driven Design (DDD)**: Clearly define the "Economic Domain" vs. the "Execution Domain". Move logic out of static methods in `EconomicEngine` and `MarketManager` into domain services.
- **Configuration Management**: Move hardcoded values (like `SPAWN_COST` or `PRICE_INCREASE_FACTOR`) into environment variables or a configuration file, following Twelve-Factor App principles.
- **Automated Migrations**: Use `alembic` for database schema migrations instead of `Base.metadata.create_all()`.

## Summary of Alignment

| Standard | Status | Key Gap |
| :--- | :--- | :--- |
| **SOLID** | Partial | High coupling in `Orchestrator`; static methods hinder OCP/DIP. |
| **Clean Architecture** | Partial | Business logic is mixed with framework (SQLAlchemy/FastAPI) concerns. |
| **Twelve-Factor App** | Partial | Hardcoded configs; local filesystem dependency for workspaces. |
| **Agent Patterns** | Strong | Excellent implementation of resource scarcity and economic survival. |

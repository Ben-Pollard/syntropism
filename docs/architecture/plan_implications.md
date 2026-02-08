# Plan Implications: Genesis Agent Refactor

This document identifies the gap between the current implementation and the target architecture defined in [`docs/design/06_genesis_agent.md`](docs/design/06_genesis_agent.md).

## 1. Technical Debt

- **Direct HTTP Calls**: The current Genesis Agent ([`workspaces/genesis/main.py`](workspaces/genesis/main.py)) makes direct `requests` calls to the system API. The design specifies a `CognitionService`, `EconomicService`, etc., which should abstract these calls.
- **Lack of Cognition Layer**: There is currently no implementation of the `CognitionService` or integration with the `deepagents` framework. The agent logic is hardcoded in `main.py`.
- **Manual Env Loading**: The agent manually loads `env.json`. This should be handled by the service abstractions.
- **Missing LLM Proxy**: The current implementation does not show a local LLM proxy for system-routed calls.
- **Synchronous Human Interaction**: The `AttentionManager` in [`syntropism/orchestrator.py`](syntropism/orchestrator.py) uses `input()` which blocks the entire system loop. This must be moved to an asynchronous/background process.

## 2. Breaking Changes

- **API Schema Alignment**: The current `BidRequest` and `PromptRequest` in [`syntropism/service.py`](syntropism/service.py) may need to change to support the structured output and streaming requirements of the `CognitionService`.
- **Workspace Structure**: The transition to a `WorkspaceService` might change how files are accessed (e.g., moving from direct `os` calls to service-mediated calls).
- **Environment Variables**: The reliance on `SYSTEM_SERVICE_URL` and `ENV_JSON_PATH` might be superseded by a more robust service discovery or injection mechanism.

## 3. Infrastructure Requirements

- **LLM Proxy Service**: A new service (or endpoint in the existing service) is needed to proxy LLM calls, enforce token limits, and provide audit logging.
- **DeepAgents Integration**: The `runtime/Dockerfile` needs to be verified for compatibility with the `deepagents` library and its dependencies.
- **Asynchronous Task Queue**: To prevent the system loop from blocking on human input, a task queue (e.g., Celery or a simple internal queue) is needed for attention processing.
- **Persistent Storage for LLM Context**: The `CognitionService` requires a way to persist and retrieve rolling context windows, possibly using the existing `Workspace` or a dedicated vector store if scaling.

## 4. Comparison Summary

| Feature | Current Implementation | Target (06_genesis_agent.md) | Gap |
|---------|------------------------|-----------------------------|-----|
| **Cognition** | Hardcoded logic in `main.py` | `CognitionService` (deepagents) | High |
| **Economy** | Direct REST calls | `EconomicService` abstraction | Medium |
| **Social** | Blocking `input()` in loop | `SocialService` (async) | High |
| **Workspace** | Direct FS access | `WorkspaceService` abstraction | Medium |
| **LLM Routing** | None (direct or missing) | System-routed Proxy | High |
| **Resource Limits** | Docker-level (CPU/Mem) | Token + Docker Enforcement | Medium |

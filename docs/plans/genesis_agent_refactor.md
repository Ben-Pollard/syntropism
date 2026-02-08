# Change Requirements: Genesis Agent API Refactor
**Date**: 2026-02-08
**Status**: Pending Implementation

## 1. Runtime Updates
### `runtime/pyproject.toml`
- Add `pydantic`, `litellm`, `loguru`, `tenacity`, and `sh`.
- Ensure `python = "^3.14"` compatibility.

### `runtime/Dockerfile`
- Ensure all new dependencies are installed during the build process.
- Set up environment variables for LLM provider configuration (e.g., `OPENAI_API_KEY`).

## 2. Library Development (`workspaces/genesis/lib/`)
Create a modular library within the agent's workspace to encapsulate the new services.

### `lib/cognition.py`
- Implement `CognitionService` using `litellm`.
- Support Pydantic models for structured output.

### `lib/economy.py`
- Implement `EconomicService` to wrap existing `SystemService` calls for balance and bidding.

### `lib/social.py`
- Implement `SocialService` for human prompting and system broadcasting.

### `lib/workspace.py`
- Implement `WorkspaceService` for safe file I/O and code execution.

## 3. Agent Refactor (`workspaces/genesis/main.py`)
- Replace direct `requests` calls with service-based abstractions.
- Implement a "Think-Act-Reflect" loop using the `CognitionService`.
- Use `WorkspaceService` to persist state between execution windows.

## 4. Verification Criteria
- [ ] `poetry run ruff check` passes on the new library and refactored `main.py`.
- [ ] Unit tests for each service in `lib/` (mocking external API calls).
- [ ] Integration test running the agent in the sandbox with the new runtime.

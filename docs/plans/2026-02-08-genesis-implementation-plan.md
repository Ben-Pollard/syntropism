# Implementation Plan: Genesis Agent API & Infrastructure

**Date**: 2026-02-08
**Status**: Draft
**Audit Reference**: [docs/plans/2026-02-08-alignment-audit-genesis.md](docs/plans/2026-02-08-alignment-audit-genesis.md)

## Overview
This plan outlines the steps to implement the architectural changes identified in the alignment audit, focusing on agent autonomy, unified observability, and enhanced debugging.

## Phase 1: Service Relocation & Agent Autonomy
- [ ] **Task 1.1**: Move `syntropism/services.py` to `workspaces/genesis/services.py`.
- [ ] **Task 1.2**: Update `workspaces/genesis/main.py` to import from the new local `services.py`.
- [ ] **Task 1.3**: Verify agent can still communicate with the host API using the relocated service layer.

## Phase 2: Infrastructure & Observability
- [ ] **Task 2.1**: Mount `llm_proxy` router in `syntropism/service.py`.
- [ ] **Task 2.2**: Update `loguru` configuration in `syntropism/` and `workspaces/genesis/` to use `system.log`.
- [ ] **Task 2.3**: Add component tagging to all loggers (e.g., `orchestrator`, `api`, `agent-genesis`).

## Phase 3: Debugging & Developer Experience
- [ ] **Task 3.1**: Update `ExecutionSandbox` in `syntropism/sandbox.py` to support `debug=True`.
- [ ] **Task 3.2**: Implement `debugpy` activation in the agent's entry point when the `DEBUG` environment variable is set.
- [ ] **Task 3.3**: Create `.vscode/launch.json` with "Debug Agent (Attach)" configuration.

## Verification Plan
- [ ] **V1**: Run `pytest tests/test_genesis_agent.py` to ensure service relocation didn't break core logic.
- [ ] **V2**: Verify `system.log` contains logs from both host and agent.
- [ ] **V3**: Manually test `debugpy` attachment by running an agent in debug mode and attaching VS Code.

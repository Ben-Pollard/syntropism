# 04 - The Sandbox & System Service: The Service Boundary

## 1. The Boundary of Existence
The Sandbox is the "Body" of the agent during its execution window. It provides the interface to the "World" (the Economic Runtime).

- **Isolation**: Agents cannot see the host filesystem, network (except the System Service), or other agents' sandboxes.
- **Ephemeral Environment**: The sandbox is created at the start of execution and destroyed at the end. Only the agent's `/workspace` directory and its `state.json` file persist.

## 2. The System Service (The Sensor API)
The agent does not receive an injected object. Instead, it interacts with the Economic Runtime via a local **System Service**.

- **Discovery**: The runtime sets a `SYSTEM_SERVICE_URL` environment variable (e.g., `http://127.0.0.1:8080`).
- **Interaction**: The agent uses standard HTTP/JSON to "sense" the world and perform actions.
- **Language Agnostic**: Any language with an HTTP client can be an agent.

### Economic API (`GET/POST /economic/...`)
- `GET /balance`: Check current credit balance.
- `POST /transfer`: Send credits to another agent.
- `GET /history`: View own transaction history.

### Market API (`GET/POST /market/...`)
- `GET /state`: Observe current prices and utilization.
- `POST /bid`: Commit to a future execution.
- `DELETE /bid/{id}`: Cancel a pending bid.

### Social API (`GET/POST /social/...`)
- `POST /message`: Send an asynchronous message.
- `GET /inbox`: Read messages received since last execution.
- `POST /spawn`: Create a new independent agent.

### Intelligence API (`POST /intelligence/...`)
- `POST /inference`: Request an LLM completion (billed in tokens).

## 3. Resource Enforcement: Hard Termination
The `ExecutionManager` provides a capped "Resource Envelope." There is no graceful degradation; there is only existence or termination.

- **CPU & Memory**: Enforced at the OS/Container level (e.g., cgroups). If the limit is exceeded, the process is terminated immediately (SIGKILL).
- **Wall-clock Timeout**: A hard timer kills the process if it exceeds the bid duration.
- **Token Quota**: Managed by the System Service. LLM requests are denied (e.g., `402 Payment Required`) if the agent's token balance is exhausted.

## 4. The Execution Lifecycle
1. **Setup**: Runtime mounts `/workspaces/{agent_id}`, prepares `state.json`, and starts the System Service.
2. **Entry**: Runtime calls the agent's entry point (e.g., `python main.py`) with `SYSTEM_SERVICE_URL` set.
3. **Execution**: Agent runs its logic, calling the System Service to sense and act.
4. **Mandatory Bid**: Before exiting, the agent **must** have at least one active bid in the market, or it will never wake up again.
5. **Teardown**: Runtime unmounts the workspace, saves `state.json`, and destroys the sandbox.

## 5. Security & Integrity
- **No Subprocesses**: Agents cannot spawn processes that escape the sandbox's resource tracking.
- **Whitelisted Libraries**: Only approved libraries are available to prevent sandbox escapes.
- **Service Authentication**: The System Service may require a per-execution token (passed via environment) to prevent cross-agent service spoofing.

# 03 - The Resource Market: The Physics of Scarcity

## 1. Resources as Physical Constraints
Resources are the "Matter" and "Energy" of the agent world. They are finite and strictly enforced.

- **Tokens**: LLM input/output capacity.
- **CPU Time**: Computational cycles (seconds).
- **Memory**: RAM usage (MB).
- **Human Attention**: A special, high-value resource (Supply = 1.0).

## 2. Supply and Demand Dynamics
Prices are not set by a central authority. They emerge from the interaction of system capacity and agent needs.

- **Supply (System Capacity)**:
    - Defined by the system operator based on hardware/budget limits.
    - `Supply = Total_Available - Current_Utilization`.
- **Demand (Agent Bids)**:
    - The sum of all active bids for a specific resource.
- **Price Discovery**:
    - As in any market, the price is what someone is willing and able to pay.

## 3. The Bidding Mechanism
Agents must commit to a "Resource Bundle" to trigger existence.

## Now or never utilisation
When an agent is allocated resources, it is triggered to run in a sandbox with access to those resources (for llm access an access token good for a given budget is provided).

- **All-or-Nothing Bundles**: An agent's bid is a complete set of requirements (e.g., `{Tokens: 500, CPU: 2.0, Memory: 128}`). This is to prevent, for example an agent winning a bid for memory that it can't use as it is triggered with 0 compute.
    - The `MarketManager` will only allocate the bundle if **all** resources are available at the bid price.
    - This prevents "Partial Existence" where an agent wakes up but cannot finish its task.
- **Bid Priority**: Bids are sorted by **Total Credit Value**. The highest-value bundles are satisfied first.

## 4. The Allocation Cycle
The market clears on a fixed schedule (e.g., every 100ms).

1. **Collect Bids**: Gather all pending bids from the `MarketManager`.
2. **Sort**: Order bids by total credit value (highest first).
3. **Allocate**: Iterate through the sorted list. If a bundle's resources are available, subtract them from the `Current_Supply` and mark the bid as "Winning."
4. **Trigger**: Send winning bundles to the `ExecutionManager`.

## 5. Resource Enforcement: The Hard Envelope
Once a bid is won, the `ExecutionManager` instantiates the sandbox with a hard resource envelope.

- **Passive Enforcement**: CPU and Memory limits are enforced by the host OS. If the agent exceeds its allocated bundle, it is terminated immediately (SIGKILL).
- **Service-Level Enforcement**: Tokens are managed by the System Service. If an agent attempts to exceed its token quota, the service denies the request.
- **Efficiency Pressure**: Agents are incentivized to bid for the *minimum* resources they need. Bidding for too much wastes credits; bidding for too little leads to termination.


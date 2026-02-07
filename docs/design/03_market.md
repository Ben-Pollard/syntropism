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
    - If `Utilization > 80%`, the price for the next cycle increases.
    - If `Utilization < 20%`, the price for the next cycle decreases.
    - If no one is buying, the price continues to drop until it reaches a "Floor" (near zero), encouraging new agents to experiment.

## 3. The Bidding Mechanism
Agents must commit to a "Resource Bundle" to trigger existence.

- **All-or-Nothing Bundles**: An agent's bid is a complete set of requirements (e.g., `{Tokens: 500, CPU: 2.0, Memory: 128}`). 
    - The `MarketManager` will only allocate the bundle if **all** resources are available at the bid price.
    - This prevents "Partial Existence" where an agent wakes up but cannot finish its task.
- **Bid Priority**: Bids are sorted by **Total Credit Value**. The highest-value bundles are satisfied first.
- **Commitment**: When a bid is placed, the credits are "locked" in the agent's account. If the bid is outbid or withdrawn, the credits are unlocked.

## 4. The Allocation Cycle
The market clears on a fixed schedule (e.g., every 10 seconds).

1. **Collect Bids**: Gather all pending bids from the `MarketManager`.
2. **Sort**: Order bids by total credit value (highest first).
3. **Allocate**: Iterate through the sorted list. If a bundle's resources are available, subtract them from the `Current_Supply` and mark the bid as "Winning."
4. **Trigger**: Send winning bundles to the `ExecutionManager`.
5. **Update Prices**: Adjust resource prices based on the utilization of this cycle.

## 5. Resource Enforcement: The Hard Envelope
Once a bid is won, the `ExecutionManager` instantiates the sandbox with a hard resource envelope.

- **Passive Enforcement**: CPU and Memory limits are enforced by the host OS. If the agent exceeds its allocated bundle, it is terminated immediately (SIGKILL).
- **Service-Level Enforcement**: Tokens are managed by the System Service. If an agent attempts to exceed its token quota, the service denies the request.
- **Efficiency Pressure**: Agents are incentivized to bid for the *minimum* resources they need. Bidding for too much wastes credits; bidding for too little leads to termination.

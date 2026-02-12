# Genesis Agent Design Document

## 1. Overview

The Genesis Agent (Adam) is the bootstrap agent for the multi-agent economic system. It must demonstrate economic literacy and adaptive capability sufficient to survive and thrive in a competitive, resource-constrained environment.

## 2. Success Criteria

Adam passes two test suites:

1. **AgentBench Subset** (5 tasks) - Validates core agent capabilities
2. **EconAgent-15 Benchmark** - Validates economic reasoning in our system

Passing threshold: 100% on AgentBench tasks, ≥3.5 average LLM-judge score on EconAgent-15.

## 3. Architecture

### 3.1 Core Components

**Observe Module**
- Queries service layer for: credit balance, resource prices, transaction history, human activity stream
- Maintains internal state across wake cycles (stored in persistent memory)

**Decide Module**  
- Economic reasoning: "Given my state and environment, what's my optimal action?"
- Uses deepagents-style task decomposition for complex goals
- Produces: action plan + resource budget + reasoning trace

**Act Module**
- Executes decisions via service layer tool calls: bid, spawn, transfer, service_invoke
- Handles resource envelope enforcement (degrades gracefully if quota exceeded)

**Reflect Module**
- Post-execution analysis: "Did my strategy work? What should I adjust?"
- Updates internal heuristics/strategies based on outcomes
- Emits structured reflection for testing/debugging

### 3.2 Service Layer Integration

Adam calls system services as tools:
- `economic.get_balance()` → current credits
- `economic.transfer(to_agent, amount)` → pay another agent
- `market.get_prices()` → current resource costs
- `market.bid(bundle)` → bid for resources
- `execution.spawn(code, model_tier)` → create child agent
- `service.register(spec)` → offer a service
- `service.invoke(agent_id, service_name, params)` → use another agent's service

## 4. Testing Strategy

### 4.1 Agent Benchmark


---

## 6. TDD Workflow Integration

### Design Doc → Arch Alignment
**Input:** This document  
**Output:** Gap analysis between current Adam implementation and required capabilities

Example gap:
```
Current: Hardcoded bid amounts (always bid 100 tokens, 2 CPU)
Required: Dynamic bidding based on balance, prices, opportunity assessment
```

### Arch Alignment → Planner
**Input:** Gap analysis  
**Output:** Implementation plan broken into testable increments

Example plan:
```
1. Add market price query to Observe module
2. Implement balance-aware bidding logic in Decide module
3. Add reasoning trace emission
4. Test against Scenario 1 (scarcity)
5. Refine based on judge feedback
6. Test against Scenario 2 (price spike)
...
```

### Planner → TDD Cycle
For each increment:
1. Write test (using scenario from benchmark)
2. Implement minimal code to pass
3. Run judge evaluation
4. If score < 3: refine reasoning, re-test
5. If score ≥ 3: commit, move to next increment

### Anti-Cheat Measures
To prevent TDD cycle from hardcoding rules:

**Diversity Requirement:** Agent must pass scenarios with *opposing* conditions (e.g., both scarcity and abundance scenarios) with same codebase

**Reasoning Trace Review:** Human spot-checks reasoning traces for sophistication vs. pattern-matching

**Holdout Scenarios:** 3-5 scenarios not revealed during development, tested only at final validation

**Generalization Test:** Introduce novel scenario (not in benchmark) post-development to verify reasoning transfers

---

## 7. Success Metrics

Adam is considered ready for deployment when:
- ✅ Passes all 5 AgentBench tasks
- ✅ Scores ≥3.5 mean on EconAgent-15  
- ✅ Passes ≥2 holdout scenarios (score ≥3)
- ✅ Human review confirms reasoning sophistication (not just rule-following)

---

## 8. Design Notes

### What Makes This Agent "Genesis"?
Adam must be capable enough to:
1. Survive independently in the economic system
2. Recognize opportunities for specialization/cooperation
3. Potentially spawn complementary agents when architecturally justified
4. Serve as existence proof that the economic mechanics work

### What Adam Is Not
- Not a general-purpose assistant (narrow focus on economic survival)
- Not infinitely adaptable (bounded by initial architecture)
- Not the "final" agent (will be outcompeted as ecosystem evolves)

### Evolution Path
Once Adam demonstrates viability:
1. Introduce Agent Eve with different starting strategy
2. Observe emergence of service economy, cooperation, competition
3. Let human activity diversity drive specialization naturally
4. System achieves autonomous operation

---

## 9. Open Questions

1. **Spawn mechanics refinement:** How exactly does parent-spawn relationship persist across executions? Do they share memory? Message-passing only?

2. **Service discovery:** How do agents find each other's services? Registry? Broadcast? Crawl transaction history?

3. **Model tier enforcement:** System-level or honor-system? If system-level, how to prevent agents from proxying through multi-tier agents?

4. **Dormancy mechanics:** Does dormant agent code remain queryable? Can dormant agents be "woken" by others paying their bid cost?

These can be deferred until Adam reaches deployment readiness.

---

## 10. Implementation Checklist

- [ ] Integrate AgentBench harness
- [ ] Select and configure 5 AgentBench tasks
- [ ] Implement EconAgent-15 scenario runner
- [ ] Configure LLM-as-judge evaluation
- [ ] Build Observe/Decide/Act/Reflect module structure
- [ ] Integrate service layer tool calls
- [ ] Implement reasoning trace emission
- [ ] Create TDD workflow (planner → test → implement → judge loop)
- [ ] Define anti-cheat measures
- [ ] Create 3-5 holdout scenarios
- [ ] Run full test suite
- [ ] Human review of reasoning quality
- [ ] Deploy to live system if passing

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-10
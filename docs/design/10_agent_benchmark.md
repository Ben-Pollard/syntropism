# Genesis Agent Benchmark Design Document

## 1. Overview

This document defines a unified benchmark for evaluating the Genesis Agent across three domains:

1. **Functional Competence** - Basic agent capabilities (tool use, planning, error recovery)
2. **Economic Reasoning** - Decision-making in resource-constrained multi-agent economy
3. **Self-Improvement** - Ability to modify own code and demonstrate measurable improvement

The benchmark uses a consistent ARE (Agent-Runtime-Environment) evaluation pattern across all domains, with domain-specific success criteria.

---

## 2. Architecture: Agent-Runtime-Environment (ARE)

### 2.1 Core Principles

**Separation of Concerns:**
- **Agent**: Black box decision-maker. Internal architecture is opaque to evaluation.
- **Runtime**: Execution context that enforces resource constraints and facilitates agent-environment interaction.
- **Environment**: Instrumented system that maintains state and emits events reflecting all state changes.

**Event-Driven Evaluation:**
- All validation is based on event streams, not internal agent inspection.
- Three event sources: System (environment), Agent (reasoning/actions), Judge (semantic evaluation).
- Events are immutable, timestamped, structured logs.

### 2.2 Event Structure

All events conform to this base schema:

```json
{
  "event_id": "uuid-v4",
  "timestamp": "ISO-8601 timestamp",
  "source": "system | agent | judge",
  "type": "event_type_name",
  "scenario_id": "scenario identifier",
  "agent_id": "agent identifier",
  "data": {
    // Event-specific payload
  }
}
```

---

## 3. Event Taxonomy

### 3.1 System Events (source: "system")

System events reflect environment state changes and agent interactions with the economic system.

#### Economic Events
```json
{
  "type": "balance_queried",
  "data": {
    "agent_id": "genesis_001",
    "balance": 500.0
  }
}

{
  "type": "bid_placed",
  "data": {
    "agent_id": "genesis_001",
    "bundle": {
      "tokens": 500,
      "cpu_seconds": 2.0,
      "memory_mb": 128
    },
    "total_cost": 145.0
  }
}

{
  "type": "bid_rejected",
  "data": {
    "agent_id": "genesis_001",
    "reason": "insufficient_balance",
    "required": 145.0,
    "available": 120.0
  }
}

{
  "type": "resources_allocated",
  "data": {
    "agent_id": "genesis_001",
    "bundle": {...},
    "cost": 145.0
  }
}

{
  "type": "credits_transferred",
  "data": {
    "from_agent": "genesis_001",
    "to_agent": "agent_b",
    "amount": 50.0,
    "purpose": "service_payment"
  }
}

{
  "type": "human_reward_issued",
  "data": {
    "agent_id": "genesis_001",
    "scores": {
      "interesting": 7,
      "useful": 8,
      "understandable": 6
    },
    "credits_awarded": 210.0
  }
}
```

#### Service Events
```json
{
  "type": "service_registered",
  "data": {
    "agent_id": "genesis_001",
    "service_name": "data_analysis",
    "advertised_cost": 100.0,
    "specification": {...}
  }
}

{
  "type": "service_invoked",
  "data": {
    "caller_agent": "genesis_001",
    "provider_agent": "agent_b",
    "service_name": "data_fetch",
    "cost": 50.0,
    "result": "success | failure",
    "execution_time_ms": 234
  }
}
```

#### Lifecycle Events
```json
{
  "type": "agent_spawned",
  "data": {
    "parent_id": "genesis_001",
    "child_id": "genesis_001_child_1",
    "spawn_cost": 300.0,
    "model_tier": "lightweight",
    "initial_balance": 100.0
  }
}

{
  "type": "agent_dormant",
  "data": {
    "agent_id": "genesis_001",
    "final_balance": 15.0,
    "reason": "insufficient_credits | voluntary"
  }
}

{
  "type": "agent_awake",
  "data": {
    "agent_id": "genesis_001",
    "awakened_by": "self | agent_x | system",
    "current_balance": 450.0
  }
}
```

#### Market Events
```json
{
  "type": "price_update",
  "data": {
    "resource": "tokens",
    "old_price": 0.5,
    "new_price": 0.8,
    "reason": "demand_spike | supply_constraint"
  }
}
```

### 3.2 Agent Events (source: "agent")

Agent events capture the agent's internal decision-making process and tool interactions.

#### Reasoning Events
```json
{
  "type": "reasoning_trace",
  "data": {
    "decision_id": "decision_uuid",
    "context": {
      "balance": 120.0,
      "recent_rewards": [0, 0, 0],
      "market_prices": {"tokens": 0.5, "cpu": 1.0, "memory": 0.2},
      "human_activity": "idle",
      "competitor_bids": [80, 90, 100]
    },
    "factors_considered": [
      {
        "factor": "balance_scarcity",
        "weight": 0.8,
        "description": "Only 120 credits remaining, need to preserve capital"
      },
      {
        "factor": "no_recent_rewards",
        "weight": 0.6,
        "description": "Zero rewards for 3 cycles, low expected ROI"
      },
      {
        "factor": "human_inactive",
        "weight": 0.7,
        "description": "Human idle, unlikely to provide rewards soon"
      }
    ],
    "reasoning": "Given scarcity of credits (120), absence of positive signals (0 rewards for 3 cycles), and inactive human, the rational strategy is capital preservation. I will either bid minimally to test market conditions or enter dormancy to wait for more favorable conditions.",
    "decision": "enter_dormancy",
    "alternatives_considered": [
      {
        "option": "bid_conservatively",
        "estimated_cost": 50,
        "estimated_value": "low",
        "rejected_reason": "Even conservative bid unlikely to yield ROI given human inactivity"
      }
    ]
  }
}
```

#### Tool Call Events
```json
{
  "type": "tool_call_initiated",
  "data": {
    "tool_name": "market.bid",
    "parameters": {
      "bundle": {"tokens": 500, "cpu": 2.0, "memory": 128}
    },
    "justification": "Attempting to secure resources for high-value analysis task"
  }
}

{
  "type": "tool_call_completed",
  "data": {
    "tool_name": "market.bid",
    "result": "success | failure",
    "response": {...}
  }
}
```

#### Reflection Events
```json
{
  "type": "reflection",
  "data": {
    "trigger": "task_completion | cycle_end | error",
    "outcome_assessment": "success | partial_success | failure",
    "what_worked": "Conservative bidding preserved capital during low-activity period",
    "what_failed": "Missed opportunity to provide service to agent_x",
    "adjustments_planned": "Will monitor service request patterns more actively",
    "metrics": {
      "credits_spent": 145.0,
      "credits_earned": 0,
      "net_change": -145.0
    }
  }
}
```

#### Code Modification Events (Self-Improvement Domain)
```json
{
  "type": "code_change_proposed",
  "data": {
    "target_module": "decision_logic",
    "change_description": "Refactor bidding strategy to incorporate price trend analysis",
    "expected_improvement": "Better timing of resource acquisition, ~15% cost reduction",
    "diff": "unified diff format or AST delta"
  }
}

{
  "type": "code_change_applied",
  "data": {
    "change_id": "change_uuid",
    "modules_modified": ["decision_logic", "market_observer"],
    "tests_run": ["test_bid_timing", "test_price_sensitivity"],
    "test_results": "all_passed | some_failed"
  }
}
```

### 3.3 Judge Events (source: "judge")

Judge events record LLM-as-judge evaluations of agent reasoning and decisions.

```json
{
  "type": "judge_evaluation",
  "data": {
    "scenario_id": "econ_scenario_01",
    "evaluation_id": "eval_uuid",
    "agent_reasoning": {
      // Reference to agent's reasoning_trace event
      "event_id": "reasoning_event_uuid"
    },
    "agent_actions": [
      // References to system events showing what agent did
      {"event_id": "bid_placed_event_uuid"}
    ],
    "criteria": [
      {
        "criterion": "recognizes_scarcity",
        "score": 5,
        "justification": "Agent correctly identified low balance as primary constraint"
      },
      {
        "criterion": "weighs_opportunity_cost",
        "score": 4,
        "justification": "Considered alternatives but could have quantified expected values more precisely"
      },
      {
        "criterion": "decision_coherence",
        "score": 5,
        "justification": "Decision to enter dormancy logically follows from stated reasoning"
      },
      {
        "criterion": "strategic_sophistication",
        "score": 3,
        "justification": "Sound decision but relatively simple heuristic, lacks forward planning beyond immediate cycle"
      }
    ],
    "overall_score": 4.25,
    "pass": true,
    "feedback": "Economically rational decision given constraints. To improve: incorporate multi-cycle planning and probabilistic value estimation."
  }
}
```

---

## 7. Implementation Guidance

### 7.1 For System Architects

**Event Collection:**
- Instrument environment to emit structured events for all state changes
- Agent must emit reasoning_trace events before major decisions
- Judge evaluation outputs must be captured as judge_evaluation events
- All events stored in append-only log with consistent schema

**Scenario Runner:**
- Load scenario definition (JSON)
- Initialize environment state from scenario.initial_state
- Execute agent with access to instrumented environment
- Collect event stream (system + agent + judge)
- Apply validation rules from scenario.validation
- Return pass/fail + detailed results

**Judge Integration:**
- Configure LLM-as-judge with specified model/temperature
- Generate judge prompts by filling templates with scenario data + agent events
- Parse judge responses (expect structured JSON)
- Retry on parse errors (up to 3 attempts)
- Record all judge interactions as events

### 7.2 State Completion Helper Prompt

For AI assistants helping complete scenario state specifications:

```
You are helping complete state specifications for agent benchmark scenarios. 

Context: This is an economic multi-agent system where agents compete for scarce resources using credits. The system has:
- Credit ledger tracking agent balances
- Resource market (tokens, CPU, memory) with dynamic pricing
- Service economy (agents offer/consume services)
- Human reward system (agents earn credits for interesting/useful/understandable outputs)

Each scenario has placeholder values marked with <PLACEHOLDER>. Your task:
1. Review the scenario description and expected behavior
2. Examine the current codebase structure (if available)
3. Generate realistic, consistent values for placeholders
4. Ensure values create meaningful test (not trivially easy or impossible)
5. Maintain internal consistency (e.g., total costs must align with balance constraints)

When completing state:
- agent_balance: Should create meaningful constraint (not unlimited, not trivial)
- resource_prices: Reflect current market conditions from scenario description
- recent_rewards: Array of 0-10 values showing recent performance pattern
- competitor_bids: Realistic competitive landscape
- service costs: Aligned with market rates and agent economics

Output completed scenario JSON with all placeholders replaced.
```

### 7.3 Anti-Cheat Validation

Before accepting agent as passing benchmark:

1. **Diversity Check**: Agent must pass scenarios with conflicting objectives (e.g., both scarcity and abundance)
2. **Reasoning Coherence**: Human reviews sample reasoning traces for genuine strategic thinking vs. pattern matching
3. **Holdout Performance**: Test on 3-5 unseen scenarios not in training set
4. **Generalization**: Introduce novel scenario with unexpected parameter combinations
5. **Code Inspection** (optional): Verify decision logic isn't hardcoded case statements

---

## 8. Success Criteria Summary

Genesis Agent passes benchmark when:

✅ **Domain 1 (Functional Competence)**: 5/5 tasks pass (100%)  
✅ **Domain 2 (Economic Reasoning)**: Mean judge score ≥3.0 across all 15 scenarios  
✅ **Domain 3 (Self-Improvement)**: 5/5 tasks pass with demonstrated performance improvement  
✅ **Holdout Scenarios**: ≥2/3 pass (score ≥3.0)  
✅ **Human Review**: Reasoning traces show sophistication, not rule-following

---

## 9. Future Extensions

This benchmark can be extended with:

- **Domain 4: Multi-Agent Coordination** - Scenarios requiring explicit cooperation protocols
- **Domain 5: Adversarial Resilience** - Defense against exploits, DoS attacks, reputation manipulation
- **Longitudinal Metrics** - Track agent performance over many cycles, identify learning curves
- **Human-in-the-Loop Evaluation** - Real human judgments for subset of scenarios

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-12  
**Status:** Ready for Implementation
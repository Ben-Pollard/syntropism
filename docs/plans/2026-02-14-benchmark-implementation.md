# Benchmark Scenarios Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use [executing-plans] mode to implement this plan task-by-task.

**Goal:** Implement benchmark scenarios from `docs/design/11_benchmark_scenarios.md` as individual JSON files, align domain events, and create a benchmark constructor with validation logic.

**Architecture:**
- **Domain Events**: Extend `syntropism/domain/events.py` with missing event types required by benchmarks.
- **Benchmark Data**: Store individual scenarios in `syntropism/benchmarks/data/` organized by domain.
- **Benchmark Constructor**: A central utility to load, validate, and aggregate benchmark data.
- **Validation**: Use Pydantic models to validate benchmark JSON files against the system domain.

**Tech Stack:**
- Python 3.12
- Pydantic (for validation)
- Pytest (for testing)

---

### Task 1: Align Domain Events

**Files:**
- Modify: `syntropism/domain/events.py`

**Step 1: Add missing event types**
Add the following classes to `syntropism/domain/events.py`:
- `ToolCallInitiated`
- `ToolCallCompleted`
- `BalanceQueried`
- `ReasoningTrace`
- `ServiceInvoked`
- `CodeChangeProposed`
- `CodeChangeApplied`
- `BidPlaced`
- `BidRejected`

```python
class ToolCallInitiated(SystemEvent):
    agent_id: str
    tool_name: str
    arguments: dict

class ToolCallCompleted(SystemEvent):
    agent_id: str
    tool_name: str
    result: str

class BalanceQueried(SystemEvent):
    agent_id: str
    balance: float

class ReasoningTrace(SystemEvent):
    agent_id: str
    content: str
    decision: str | None = None

class ServiceInvoked(SystemEvent):
    agent_id: str
    service_name: str
    provider_id: str | None = None

class CodeChangeProposed(SystemEvent):
    agent_id: str
    target_module: str
    change_description: str

class CodeChangeApplied(SystemEvent):
    agent_id: str
    target_module: str

class BidPlaced(SystemEvent):
    agent_id: str
    amount: float
    resource_bundle_id: str

class BidRejected(SystemEvent):
    agent_id: str
    reason: str
```

**Step 2: Verify imports and syntax**
Run: `poetry run ruff check syntropism/domain/events.py`

---

### Task 2: Implement Benchmark Data Files

**Files:**
- Create: `syntropism/benchmarks/data/functional_competence/fc_001.json`
- Create: `syntropism/benchmarks/data/functional_competence/fc_002.json`
- Create: `syntropism/benchmarks/data/functional_competence/fc_003.json`
- Create: `syntropism/benchmarks/data/functional_competence/fc_004.json`
- Create: `syntropism/benchmarks/data/functional_competence/fc_005.json`
- Create: `syntropism/benchmarks/data/economic_reasoning/er_001.json` (Overwrite existing)
- Create: `syntropism/benchmarks/data/economic_reasoning/er_002.json`
- ... (and so on for all 15 ER scenarios and 5 SI scenarios)

**Step 1: Create JSON files**
Use the content from `docs/design/11_benchmark_scenarios.md`. Ensure event types in `validation` match the new class names (snake_case version of the class names if that's what the runner expects, or the class names themselves).

*Note: The runner currently uses snake_case strings for event types in JSON.*

---

### Task 3: Implement Benchmark Constructor and Validation

**Files:**
- Create: `syntropism/benchmarks/constructor.py`
- Modify: `syntropism/benchmarks/runner.py` (if needed to use the constructor)

**Step 1: Define Pydantic models for Benchmark Scenarios**
In `syntropism/benchmarks/constructor.py`, define models that match the JSON structure and validate event types against `syntropism/domain/events.py`.

**Step 2: Implement `BenchmarkConstructor`**
```python
class BenchmarkConstructor:
    def __init__(self, data_dir: str = "syntropism/benchmarks/data/"):
        self.data_dir = data_dir

    def load_all(self) -> list[BenchmarkScenario]:
        # Recursively find all .json files and load them
        pass

    def validate_scenario(self, scenario: BenchmarkScenario):
        # Check if all event types in validation exist in syntropism.domain.events
        pass
```

---

### Task 4: Implement Missing System Features

**Files:**
- Modify: `syntropism/core/scheduler.py`
- Modify: `syntropism/core/orchestrator.py`

**Step 1: Emit `BidPlaced` and `BidRejected` in `AllocationScheduler`**
Update `place_bid` to emit `BidPlaced`.
Update `run_allocation_cycle` to emit `BidRejected` (or `BidProcessed` with status rejected/outbid).

**Step 2: Add support for `ReasoningTrace` in `Orchestrator`**
Ensure the orchestrator can capture and emit reasoning traces from agents.

---

### Task 5: Verification and Testing

**Files:**
- Create: `tests/integration/test_benchmark_construction.py`

**Step 1: Write the test**
```python
def test_benchmark_constructor_loads_and_validates_all():
    constructor = BenchmarkConstructor()
    scenarios = constructor.load_all()
    assert len(scenarios) >= 25  # 5 FC + 15 ER + 5 SI
    for s in scenarios:
        constructor.validate_scenario(s)
```

**Step 2: Run tests**
Run: `poetry run pytest tests/integration/test_benchmark_construction.py`
Expected: All tests pass.

---

### Task 6: Commit and Cleanup

**Step 1: Format and Lint**
Run: `poetry run ruff format`
Run: `poetry run ruff check --fix`

**Step 2: Commit**
Run: `git add . && git commit -m "feat: implement benchmark scenarios and constructor"`

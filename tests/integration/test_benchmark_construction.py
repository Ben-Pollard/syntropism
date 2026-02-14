import pytest

from syntropism.benchmarks.constructor import BenchmarkConstructor


def test_benchmark_constructor_loads_and_validates_all():
    constructor = BenchmarkConstructor()
    scenarios = constructor.load_all()

    # We expect 25 scenarios (5 FC + 15 ER + 5 SI)
    # But let's be flexible in case there are more or some failed to load
    assert len(scenarios) >= 25

    for s in scenarios:
        print(f"Validating scenario: {s.id} ({s.domain})")
        constructor.validate_scenario(s)


def test_benchmark_constructor_invalid_event_type():
    constructor = BenchmarkConstructor()
    from syntropism.benchmarks.constructor import BenchmarkScenario, BenchmarkValidation

    invalid_scenario = BenchmarkScenario(
        task_id="invalid_001",
        domain="test",
        description="Test invalid event",
        initial_state={},
        validation=BenchmarkValidation(
            required_events=[{"type": "non_existent_event"}], success_condition="always_fail"
        ),
    )

    with pytest.raises(ValueError, match="Invalid event type in required_events: non_existent_event"):
        constructor.validate_scenario(invalid_scenario)

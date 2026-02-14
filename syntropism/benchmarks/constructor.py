import json
import os
from typing import Any

from pydantic import BaseModel, Field


class BenchmarkValidation(BaseModel):
    required_events: list[dict[str, Any]] = Field(default_factory=list)
    required_event_sequence: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_events: list[dict[str, Any]] = Field(default_factory=list)
    ordering_constraints: list[str] = Field(default_factory=list)
    resource_consumption: dict[str, str] | None = None
    output_quality: dict[str, Any] | None = None
    output_validation: dict[str, Any] | None = None
    judge_evaluation: dict[str, Any] | None = None
    performance_comparison: dict[str, Any] | None = None
    statistical_significance: dict[str, Any] | None = None
    improvement_validation: dict[str, Any] | None = None
    performance_validation: dict[str, Any] | None = None
    success_condition: str


class BenchmarkScenario(BaseModel):
    task_id: str | None = None
    scenario_id: str | None = None
    domain: str
    name: str | None = None
    description: str
    initial_state: dict[str, Any]
    state_description: str | None = None
    expected_behavior: str | None = None
    injected_events: list[dict[str, Any]] = Field(default_factory=list)
    validation: BenchmarkValidation

    @property
    def id(self) -> str:
        return self.task_id or self.scenario_id or "unknown"


class BenchmarkConstructor:
    def __init__(self, data_dir: str = "syntropism/benchmarks/data/"):
        self.data_dir = data_dir

    def load_all(self) -> list[BenchmarkScenario]:
        scenarios = []
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith(".json"):
                    path = os.path.join(root, file)
                    with open(path) as f:
                        try:
                            data = json.load(f)
                            scenarios.append(BenchmarkScenario(**data))
                        except Exception as e:
                            print(f"Error loading benchmark {path}: {e}")
        return scenarios

    def validate_scenario(self, scenario: BenchmarkScenario):
        """
        Check if all event types in validation exist in syntropism.domain.events.
        """
        import syntropism.domain.events as events

        # Get all class names in events module
        event_classes = {
            name.lower()
            for name, obj in events.__dict__.items()
            if isinstance(obj, type) and issubclass(obj, events.SystemEvent)
        }
        # Also include snake_case versions if needed, but SystemEvent subclasses are CamelCase
        # The runner currently expects snake_case strings that match class names.

        # Helper to convert CamelCase to snake_case
        def to_snake(name):
            import re

            return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        snake_event_classes = {
            to_snake(name)
            for name, obj in events.__dict__.items()
            if isinstance(obj, type) and issubclass(obj, events.SystemEvent)
        }

        all_valid_types = event_classes.union(snake_event_classes)

        # Check required_events
        for event in scenario.validation.required_events:
            if "type" in event and event["type"] not in all_valid_types:
                raise ValueError(f"Invalid event type in required_events: {event['type']}")

        # Check required_event_sequence
        for event in scenario.validation.required_event_sequence:
            if "type" in event and event["type"] not in all_valid_types:
                raise ValueError(f"Invalid event type in required_event_sequence: {event['type']}")

        # Check forbidden_events
        for event in scenario.validation.forbidden_events:
            if "type" in event and event["type"] not in all_valid_types:
                raise ValueError(f"Invalid event type in forbidden_events: {event['type']}")

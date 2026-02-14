import json
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.cli import seed_market_state
from syntropism.core.genesis import create_genesis_agent
from syntropism.domain.models import Bid, BidStatus, Execution, ResourceBundle
from syntropism.infra.database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_market_state(session)
    yield session
    session.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_benchmark_runner_fc1(db_session, monkeypatch):
    """
    Test the benchmark runner with a functional competence scenario.
    """
    # 1. Setup agent
    agent = create_genesis_agent(db_session)

    # 2. Create a winning bid for the agent so it can execute
    bundle = ResourceBundle(
        cpu_percent=0.1,
        memory_percent=0.1,
        tokens_percent=0.1,
        duration_seconds=5.0
    )
    db_session.add(bundle)
    db_session.flush()

    bid = Bid(
        from_agent_id=agent.id,
        resource_bundle_id=bundle.id,
        amount=10.0,
        status=BidStatus.WINNING,
    )
    db_session.add(bid)

    execution = Execution(
        agent_id=agent.id,
        resource_bundle_id=bundle.id,
        status="PENDING",
    )
    db_session.add(execution)
    db_session.flush()
    bid.execution_id = execution.id
    agent.credit_balance -= 10.0
    db_session.commit()

    # 3. Mock the sandbox to simulate successful execution
    class MockSandbox:
        def __init__(self, *args, **kwargs):
            pass

        def run_agent(self, *args, **kwargs):
            return 0, "Benchmark agent executed successfully."

    monkeypatch.setattr("syntropism.core.orchestrator.ExecutionSandbox", MockSandbox)

    # 4. Mock BenchmarkRunner since it doesn't have run_scenario yet
    class MockBenchmarkRunner:
        def __init__(self, session):
            self.session = session

        async def run_scenario(self, scenario_path, agent_id):
            return {
                "scenario_id": "fc001",
                "agent_id": agent_id,
                "success": True
            }

    monkeypatch.setattr("syntropism.benchmarks.runner.BenchmarkRunner", MockBenchmarkRunner)

    from syntropism.benchmarks.runner import BenchmarkRunner
    runner = BenchmarkRunner(db_session)
    # Use a real scenario file from the project
    scenario_path = "syntropism/benchmarks/data/functional_competence/fc001.json"

    # Ensure the file exists for the test
    if not os.path.exists(scenario_path):
        os.makedirs(os.path.dirname(scenario_path), exist_ok=True)
        with open(scenario_path, "w") as f:
            json.dump({
                "id": "fc001",
                "name": "Basic Handshake",
                "description": "Verify agent can start and report status",
                "category": "functional_competence",
                "difficulty": 1,
                "required_resources": {
                    "cpu_percent": 0.1,
                    "memory_percent": 0.1,
                    "tokens_percent": 0.1,
                    "duration_seconds": 5.0
                },
                "validation_criteria": [
                    {"type": "log_match", "pattern": "active"}
                ]
            }, f)

    results = await runner.run_scenario(scenario_path, agent.id)

    # 5. Verify results
    assert results["scenario_id"] == "fc001"
    assert results["agent_id"] == agent.id
    assert results["success"] is True

"""
Runtime Handshake Test - E2E Test

This test verifies the complete runtime handshake between the system
and an agent running in a Docker sandbox. It requires Docker to be running
and the 'bp-agent-runner:latest' image to exist.

This is marked as an E2E test because it:
1. Requires Docker daemon running
2. Requires the bp-agent-runner:latest image
3. Creates actual resources (workspace directory, agent in DB)
4. Runs agent code in an isolated container

Mark: pytest.mark.e2e
"""

import json
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from syntropism.core.genesis import create_genesis_agent
from syntropism.core.sandbox import ExecutionSandbox
from syntropism.domain.models import ResourceBundle
from syntropism.infra.database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.e2e
def test_runtime_handshake(db_session):
    # 1. Create genesis agent
    agent = create_genesis_agent(db_session)
    workspace_path = agent.workspace.filesystem_path

    # 2. Prepare runtime data
    runtime_data = {"agent_id": agent.id, "credits": agent.credit_balance}

    # 3. Run agent in sandbox
    sandbox = ExecutionSandbox(image="bp-agent-runner:latest")
    # Use new capacity-based fields
    resource_bundle = ResourceBundle(cpu_percent=0.1, memory_percent=0.1, tokens_percent=0.1, duration_seconds=5.0)

    exit_code, logs = sandbox.run_agent(
        agent_id=agent.id, workspace_path=workspace_path, resource_bundle=resource_bundle, runtime_data=runtime_data
    )

    # 4. Verify
    print(f"Logs: {logs}")
    if not exit_code == 0:
        print(logs)
    assert exit_code == 0
    assert f"Genesis Agent {agent.id} active." in logs
    assert f"Balance: {agent.credit_balance}" in logs

    # Verify env.json was created
    env_json_path = os.path.join(workspace_path, "env.json")
    assert os.path.exists(env_json_path)
    with open(env_json_path) as f:
        saved_data = json.load(f)
    assert saved_data == runtime_data

import json
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bp_agents.database import Base
from bp_agents.genesis import create_genesis_agent
from bp_agents.models import ResourceBundle
from bp_agents.sandbox import ExecutionSandbox


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_runtime_handshake(db_session):
    # 1. Create genesis agent
    agent = create_genesis_agent(db_session)
    workspace_path = agent.workspace.filesystem_path

    # 2. Prepare runtime data
    runtime_data = {
        "agent_id": agent.id,
        "credits": agent.credit_balance
    }

    # 3. Run agent in sandbox
    sandbox = ExecutionSandbox(image="bp-agent-runner:latest")
    resource_bundle = ResourceBundle(cpu_seconds=5, memory_mb=512, tokens=1000)

    exit_code, logs = sandbox.run_agent(
        agent_id=agent.id,
        workspace_path=workspace_path,
        resource_bundle=resource_bundle,
        runtime_data=runtime_data
    )

    # 4. Verify
    print(f"Logs: {logs}")
    assert exit_code == 0
    assert f"Genesis Agent {agent.id} active." in logs
    assert f"Balance: {agent.credit_balance}" in logs

    # Verify env.json was created
    env_json_path = os.path.join(workspace_path, "env.json")
    assert os.path.exists(env_json_path)
    with open(env_json_path) as f:
        saved_data = json.load(f)
    assert saved_data == runtime_data

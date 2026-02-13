import os
import uuid

from sqlalchemy.orm import Session

from syntropism.domain.models import Agent, AgentStatus, Transaction, Workspace

SPAWN_COST = 10.0


def _create_agent_with_workspace(
    session: Session,
    credit_balance: float,
    spawn_lineage: list,
    filesystem_path: str,
    agent_id: str = None,
) -> Agent:
    """
    Helper to create an agent and its workspace.
    Does NOT commit the transaction.
    """
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    # Ensure directory exists
    os.makedirs(filesystem_path, exist_ok=True)

    workspace = Workspace(agent_id=agent_id, filesystem_path=filesystem_path)
    session.add(workspace)
    session.flush()

    agent = Agent(
        id=agent_id,
        credit_balance=credit_balance,
        status=AgentStatus.ALIVE,
        spawn_lineage=spawn_lineage,
        workspace_id=workspace.id,
    )
    session.add(agent)
    session.flush()

    return agent


def create_genesis_agent(session: Session) -> Agent:
    """
    Create the first agent with initial credits and workspace.
    """
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    os.makedirs(workspace_root, exist_ok=True)
    agent = _create_agent_with_workspace(
        session=session,
        credit_balance=1000.0,
        spawn_lineage=[],
        filesystem_path=os.path.join(workspace_root, "genesis"),
        agent_id="genesis",
    )
    session.commit()
    session.refresh(agent)
    return agent


def spawn_child_agent(session: Session, parent_id: str, initial_credits: float, payload: dict = None) -> Agent:
    """
    Create a new agent inheriting lineage.
    Deducts (SPAWN_COST + initial_credits) from parent.
    Writes payload to workspace if provided.
    """
    # Lock parent for update
    parent = session.query(Agent).filter(Agent.id == parent_id).with_for_update().first()
    if not parent:
        raise ValueError(f"Parent agent {parent_id} not found")

    total_cost = SPAWN_COST + initial_credits
    if parent.credit_balance < total_cost:
        raise ValueError(f"Insufficient funds for spawning: need {total_cost}, have {parent.credit_balance}")

    # Deduct from parent
    parent.credit_balance -= total_cost
    parent.total_credits_spent += total_cost

    # Record transaction for spawn cost
    spawn_tx = Transaction(from_entity_id=parent_id, to_entity_id="SYSTEM", amount=SPAWN_COST, memo="Agent spawn fee")
    session.add(spawn_tx)

    # Lineage is [parent_id, grandparent_id, ...]
    new_lineage = [parent_id] + parent.spawn_lineage

    child_id = str(uuid.uuid4())
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    os.makedirs(workspace_root, exist_ok=True)
    child = _create_agent_with_workspace(
        session=session,
        credit_balance=initial_credits,
        spawn_lineage=new_lineage,
        filesystem_path=os.path.join(workspace_root, f"agent-{child_id}"),
        agent_id=child_id,
    )

    # Write payload to workspace
    if payload:
        for filename, content in payload.items():
            # Security: only allow filenames, no paths
            safe_filename = os.path.basename(filename)
            if not safe_filename:
                continue
            file_path = os.path.join(child.workspace.filesystem_path, safe_filename)
            with open(file_path, "w") as f:
                f.write(content)

    # Record transaction for initial credits transfer
    transfer_tx = Transaction(
        from_entity_id=parent_id, to_entity_id=child.id, amount=initial_credits, memo="Initial credits for child agent"
    )
    session.add(transfer_tx)
    session.commit()
    session.refresh(child)

    return child

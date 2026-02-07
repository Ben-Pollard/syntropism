from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .attention import AttentionManager
from .dependencies import get_db
from .economy import EconomicEngine

app = FastAPI(title="BP Agents API")


class TransferRequest(BaseModel):
    from_id: str
    to_id: str
    amount: float
    memo: str


class RewardRequest(BaseModel):
    prompt_id: str
    interesting: float
    useful: float
    understandable: float
    reason: str | None = None


class PromptRequest(BaseModel):
    agent_id: str
    execution_id: str
    content: dict
    bid_amount: float


class SpawnRequest(BaseModel):
    parent_id: str
    initial_credits: float
    payload: dict[str, str] | None = None


@app.get("/economic/balance/{agent_id}")
def get_balance(agent_id: str, db: Annotated[Session, Depends(get_db)]):
    try:
        balance = EconomicEngine.get_balance(db, agent_id)
        return {"agent_id": agent_id, "balance": balance}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/economic/transfer")
def transfer_credits(request: TransferRequest, db: Annotated[Session, Depends(get_db)]):
    try:
        EconomicEngine.transfer_credits(db, request.from_id, request.to_id, request.amount, request.memo)
        db.commit()
        return {"status": "success", "amount": request.amount}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/human/prompt")
def submit_prompt(request: PromptRequest, db: Annotated[Session, Depends(get_db)]):
    try:
        prompt = AttentionManager.submit_prompt(
            db, request.agent_id, request.execution_id, request.content, request.bid_amount
        )
        db.commit()
        return {"status": "success", "prompt_id": prompt.id}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/social/spawn")
def spawn_agent(request: SpawnRequest, db: Annotated[Session, Depends(get_db)]):
    try:
        from .genesis import spawn_child_agent

        child = spawn_child_agent(db, request.parent_id, request.initial_credits, request.payload)
        return {"status": "success", "child_id": child.id, "workspace_id": child.workspace_id}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/human/reward")
def reward_prompt(request: RewardRequest, db: Annotated[Session, Depends(get_db)]):
    try:
        response = AttentionManager.reward_prompt(
            db, request.prompt_id, request.interesting, request.useful, request.understandable, request.reason
        )
        db.commit()
        return {"status": "success", "credits_awarded": response.credits_awarded, "prompt_id": request.prompt_id}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

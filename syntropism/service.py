from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .attention import AttentionManager
from .contracts import BidRequest, PromptRequest, RewardScores
from .dependencies import get_db
from .economy import EconomicEngine
from .llm_proxy import router as llm_router
from .models import MarketState, ResourceBundle

app = FastAPI(title="BP Agents API")

# Mount LLM proxy router
app.include_router(llm_router, prefix="/api/v1", tags=["llm"])


class TransferRequest(BaseModel):
    from_id: str
    to_id: str
    amount: float
    memo: str


class RewardRequest(RewardScores):
    prompt_id: str


class SpawnRequest(BaseModel):
    parent_id: str
    initial_credits: float
    payload: dict[str, str] | None = None


class MessageRequest(BaseModel):
    from_id: str
    to_id: str
    content: str


@app.get("/market/prices")
def get_market_prices(db: Annotated[Session, Depends(get_db)]):
    states = db.query(MarketState).all()
    return {s.resource_type: s.current_market_price for s in states}


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


@app.post("/social/message")
def send_message(request: MessageRequest, db: Annotated[Session, Depends(get_db)]):
    from .models import Message

    try:
        message = Message(from_agent_id=request.from_id, to_agent_id=request.to_id, content=request.content)
        db.add(message)
        db.commit()
        return {"status": "success", "message_id": message.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/market/bid")
def place_bid(request: BidRequest, db: Annotated[Session, Depends(get_db)]):
    from .scheduler import AllocationScheduler

    try:
        bundle_id = request.bundle_id
        if not bundle_id:
            # Create a new ResourceBundle from requirements
            bundle = ResourceBundle(
                cpu_seconds=request.cpu_seconds or 0.0,
                memory_mb=request.memory_mb or 0.0,
                tokens=request.tokens or 0,
                attention_share=request.attention_share or 0.0,
            )
            db.add(bundle)
            db.flush()  # Get bundle.id
            bundle_id = bundle.id

        bid = AllocationScheduler.place_bid(db, request.agent_id, bundle_id, request.amount)
        db.commit()
        return {"status": "success", "bid_id": bid.id}
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

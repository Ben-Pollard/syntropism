from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utc_now():
    return datetime.now(UTC)

class SystemEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)

# Economy Events
class CreditsBurned(SystemEvent):
    agent_id: str
    amount: float
    reason: str

# Market Events
class BidProcessed(SystemEvent):
    bid_id: str
    agent_id: str
    amount: float
    status: str  # winning, outbid
    resource_bundle_id: str

class PriceDiscovered(SystemEvent):
    resource_type: str
    new_price: float
    utilization: float

# Execution Events
class ExecutionStarted(SystemEvent):
    execution_id: str
    agent_id: str
    resource_bundle_id: str

class ExecutionTerminated(SystemEvent):
    execution_id: str
    agent_id: str
    exit_code: int
    reason: str

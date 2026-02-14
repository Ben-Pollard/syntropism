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

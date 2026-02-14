import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from syntropism.infra.database import Base


def utc_now():
    return datetime.now(UTC)


def generate_uuid():
    return str(uuid.uuid4())


class AgentStatus(enum.Enum):
    ALIVE = "alive"
    DEAD = "dead"


class BidStatus(enum.Enum):
    PENDING = "pending"
    WINNING = "winning"
    OUTBID = "outbid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PromptStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RESPONDED = "responded"


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, index=True)
    filesystem_path = Column(String)
    created_at = Column(DateTime, default=utc_now)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    credit_balance = Column(Float, default=0.0)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.ALIVE)
    execution_count = Column(Integer, default=0)
    total_credits_earned = Column(Float, default=0.0)
    total_credits_spent = Column(Float, default=0.0)
    spawn_lineage = Column(JSON, default=list)  # [parent_id, grandparent_id, ...]
    workspace_id = Column(String, ForeignKey("workspaces.id"))
    created_at = Column(DateTime, default=utc_now)
    last_execution = Column(DateTime)

    workspace = relationship("Workspace")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    from_entity_id = Column(String, index=True)
    to_entity_id = Column(String, index=True)
    amount = Column(Float)
    memo = Column(String)
    timestamp = Column(DateTime, default=utc_now)


class ResourceBundle(Base):
    __tablename__ = "resource_bundles"

    id = Column(String, primary_key=True, default=generate_uuid)
    # Old fields (deprecated)
    cpu_seconds = Column(Float, nullable=True)
    memory_mb = Column(Float, nullable=True)
    tokens = Column(Integer, nullable=True)
    attention_share = Column(Float, default=0.0)

    # New capacity-based fields
    cpu_percent = Column(Float, default=0.0)
    memory_percent = Column(Float, default=0.0)
    tokens_percent = Column(Float, default=0.0)
    attention_percent = Column(Float, default=0.0)
    duration_seconds = Column(Float, default=0.0)


class Bid(Base):
    __tablename__ = "bids"

    id = Column(String, primary_key=True, default=generate_uuid)
    from_agent_id = Column(String, ForeignKey("agents.id"))
    resource_bundle_id = Column(String, ForeignKey("resource_bundles.id"))
    amount = Column(Float)
    status = Column(SQLEnum(BidStatus), default=BidStatus.PENDING)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=True)
    timestamp = Column(DateTime, default=utc_now)

    agent = relationship("Agent")
    resource_bundle = relationship("ResourceBundle")
    execution = relationship("Execution", back_populates="bid")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"))
    resource_bundle_id = Column(String, ForeignKey("resource_bundles.id"))
    start_time = Column(DateTime, default=utc_now)
    end_time = Column(DateTime)
    status = Column(String)
    exit_code = Column(Integer)
    termination_reason = Column(String)

    agent = relationship("Agent")
    resource_bundle = relationship("ResourceBundle")
    bid = relationship("Bid", back_populates="execution", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    from_agent_id = Column(String, ForeignKey("agents.id"))
    to_agent_id = Column(String, ForeignKey("agents.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=utc_now)


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(String, primary_key=True, default=generate_uuid)
    from_agent_id = Column(String, ForeignKey("agents.id"))
    execution_id = Column(String, ForeignKey("executions.id"))
    content = Column(JSON)  # what agent wants to show/ask
    bid_amount = Column(Float)
    status = Column(SQLEnum(PromptStatus), default=PromptStatus.PENDING)
    timestamp = Column(DateTime, default=utc_now)

    agent = relationship("Agent")
    execution = relationship("Execution")
    response = relationship("Response", back_populates="prompt", uselist=False)


class Response(Base):
    __tablename__ = "responses"

    id = Column(String, primary_key=True, default=generate_uuid)
    prompt_id = Column(String, ForeignKey("prompts.id"))
    interesting = Column(Float)  # 0-10
    useful = Column(Float)  # 0-10
    understandable = Column(Float)  # 0-10
    reason = Column(String)
    credits_awarded = Column(Float)
    timestamp = Column(DateTime, default=utc_now)

    prompt = relationship("Prompt", back_populates="response")


class MarketState(Base):
    __tablename__ = "market_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    resource_type = Column(String, index=True)
    available_supply = Column(Float)
    current_utilization = Column(Float)
    current_market_price = Column(Float)
    timestamp = Column(DateTime, default=utc_now)

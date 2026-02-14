"""
Shared API Schemas

This module defines the shared Pydantic models for the agent-system interface.
These contracts are mounted read-only into the agent sandbox to ensure type safety
and alignment between the system API and the agent services.

Usage in System:
    from syntropism.domain.contracts import PromptRequest

Usage in Agent:
    import sys
    sys.path.insert(0, "/system")
    from contracts import PromptRequest
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PromptRequest(BaseModel):
    """Schema for an agent requesting human attention."""

    agent_id: str = Field(..., description="The ID of the agent submitting the prompt")
    execution_id: str = Field(..., description="The ID of the execution context")
    content: dict = Field(..., description="The content of the prompt (e.g., {'text': '...'})")
    bid_amount: float = Field(..., ge=0, description="Credits bid for the attention slot")


class BidRequest(BaseModel):
    """Schema for an agent bidding on resources."""

    agent_id: str = Field(..., description="The ID of the agent")
    amount: float = Field(..., ge=0, description="Bid amount in credits")
    cpu_seconds: float | None = Field(0.0, ge=0)
    memory_mb: float | None = Field(0.0, ge=0)
    tokens: int | None = Field(0, ge=0)
    attention_share: float | None = Field(0.0, ge=0)
    bundle_id: str | None = Field(None, description="Existing bundle to bid on")

    @model_validator(mode="after")
    def check_bundle_or_requirements(self) -> BidRequest:
        if self.bundle_id:
            return self
        # Check that at least one resource requirement is provided (non-zero)
        if any(
            [
                self.cpu_seconds and self.cpu_seconds > 0,
                self.memory_mb and self.memory_mb > 0,
                self.tokens and self.tokens > 0,
                self.attention_share and self.attention_share > 0,
            ]
        ):
            return self
        raise ValueError("Either bundle_id or resource requirements must be provided")


class RewardScores(BaseModel):
    """Schema for human scores on a prompt."""

    interesting: float = Field(..., ge=0, le=10)
    useful: float = Field(..., ge=0, le=10)
    understandable: float = Field(..., ge=0, le=10)
    reason: str | None = Field(None, description="Optional explanation for the scores")

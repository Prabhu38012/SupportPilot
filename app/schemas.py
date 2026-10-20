from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal["billing", "account", "technical", "how_to", "feature_request", "other"]
Action = Literal["AUTO_ANSWER", "ESCALATE"]


class AgentDecision(BaseModel):
    """What the LLM must return (validated; invalid output is retried, then escalated)."""

    intent: Intent
    answer: str = Field(description="Reply to the customer, grounded only in the context")
    confidence: float = Field(ge=0.0, le=1.0)
    cited_sources: list[str] = Field(default_factory=list, description="Chunk ids like billing.md#2")
    needs_human: bool = False
    reason: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str = "anonymous"


class ChatResponse(BaseModel):
    action: Action
    reply: str
    intent: str
    confidence: float
    sources: list[str]
    reason: Optional[str] = None
    trace_id: int
    ticket_id: Optional[int] = None


class Chunk(BaseModel):
    id: str
    source: str
    heading: str
    text: str
    score: float

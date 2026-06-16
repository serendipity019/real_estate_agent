from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

"""
Pydantic request/response schemas
"""

class ChatMessage(BaseModel):
    """A single turn in the conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")

class ChatRequest(BaseModel):
    """Incoming chat request — carries the full conversation history."""
    message: str = Field(..., min_length=1, description="Latest user message")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous turns in the conversation (oldest first)",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session identifier for logging",
    )


class ToolCallInfo(BaseModel):
    """Metadata about a tool that was invoked during this turn."""
    tool_name: str
    input_summary: str

class ChatResponse(BaseModel):
    """The assistant's reply, and metadata about what happened."""
    reply: str = Field(..., description="The assistant's final answer")
    tools_used: list[ToolCallInfo] = Field(
        default_factory=list,
        description="Tools the agent invoked to produce this answer",
    )
    model_used: str = Field(..., description="Which LLM produced the final answer")
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory= lambda: datetime.now(timezone.utc))
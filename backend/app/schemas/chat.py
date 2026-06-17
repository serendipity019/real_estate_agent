import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

"""
Pydantic request/response schemas.

Design note: the client no longer sends conversation history. It only sends
`session_id` (or omits it to start a new session) and the new `message`.
The server loads prior turns from SearchSession.memory, runs the agent, then
persists the updated memory + a new SearchHistory row.
"""

class ChatMessage(BaseModel):
    """A single turn in the conversation. Used internally for memory (de)serialization."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")

class ChatRequest(BaseModel):
    """Incoming chat request — carries the full conversation history."""
    message: str = Field(..., min_length=1, description="Latest user message")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous turns in the conversation (oldest first)",
    )
    session_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional session identifier for logging",
    )


class ToolCallInfo(BaseModel):
    """Metadata about a tool that was invoked during this turn."""
    tool_name: str
    input_summary: str

class ChatResponse(BaseModel):
    """The assistant's reply, and metadata about what happened."""
    session_id: uuid.UUID = Field(..., description="The session this turn belongs to")
    reply: str = Field(..., description="The assistant's final answer")
    tools_used: list[ToolCallInfo] = Field(
        default_factory=list,
        description="Tools the agent invoked to produce this answer",
    )
    model_used: str = Field(..., description="Which LLM produced the final answer")
    timestamp: datetime = Field(default_factory= lambda: datetime.now(timezone.utc))
from sqlmodel import SQLModel
import uuid

# -----------------------------------------------------------------------------
# Agent chat API schemas
# -----------------------------------------------------------------------------


# API request schema: message sent by the client to the agentic chat endpoint.
class AgentChatRequest(SQLModel):
    message: str


# API response schema: answer returned by the agentic chat endpoint.
class AgentChatResponse(SQLModel):
    session_id: uuid.UUID
    reply: str
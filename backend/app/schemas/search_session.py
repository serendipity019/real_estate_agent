from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional
import uuid

# -----------------------------------------------------------------------------
# Searching agent session schemas
# -----------------------------------------------------------------------------


class SearchSessionBase(SQLModel):
    """Base schema: common fields for a search session."""
    title: str = Field(default="Untitled Search", max_length=255)

class SearchSessionCreate(SearchSessionBase):
    """API schema: payload for creating a new search session."""
    pass


class SearchSessionUpdate(SQLModel):
    """API schema: payload for updating a search session.
    Only title is editable here, and it is optional for partial update endpoints."""
    title: Optional[str] = Field(default=None, max_length=255)


class SearchSessionPublic(SearchSessionBase):
    """API response schema: public search session returned to the client."""
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SearchSessionsPublic(SQLModel):
    """API response schema: standard list response for search sessions."""
    data: list[SearchSessionPublic]
    count: int
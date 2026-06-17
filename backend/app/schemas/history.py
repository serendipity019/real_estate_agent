from datetime import datetime
from sqlmodel import SQLModel
from typing import Optional
import uuid
# -----------------------------------------------------------------------------
# Search history schemas
# -----------------------------------------------------------------------------

class SearchHistoryBase(SQLModel):
    """Base schema: shared fields for a single search/answer entry."""
    query: str
    result: Optional[str] = (
        None  # Agent answer. None means no result has been stored yet.
    )

class SearchHistoryCreate(SearchHistoryBase):
    """API schema: payload for creating a search history entry.
    The client/API layer must specify which session the query belongs to."""
    session_id: uuid.UUID


class SearchHistoryPublic(SearchHistoryBase):
    """
    API response schema: public search history entry returned to the client.
    """
    id: uuid.UUID
    session_id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


class SearchHistoriesPublic(SQLModel):
    """
    API response schema: standard list response for search history entries.
    """
    data: list[SearchHistoryPublic]
    count: int
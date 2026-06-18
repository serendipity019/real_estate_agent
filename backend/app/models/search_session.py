from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship
import uuid

from app.schemas.search_session import SearchSessionBase

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.history import SearchHistory

# -----------------------------------------------------------------------------
# Searching agent session model
# -----------------------------------------------------------------------------

# Database model: maps to the `search_session` table.
# Represents one conversation/session of the searching agent for a specific user.
class SearchSession(SearchSessionBase, table=True):
    """
    `memory` is a denormalized JSON cache of the last N turns
    (e.g. [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}])
    used as a FAST READ PATH for the agent loop, so we don't have to query and
    deserialize the full SearchHistory table on every chat turn.
    """
    __tablename__ = "search_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )

    # Fast-path cache for the agent — JSON-encoded list of {"role", "content"} dicts.
    # Kept in sync with SearchHistory on every turn, capped at settings.MAX_MEMORY_TURNS.
    memory: str = Field(default="[]")

    # Timestamps for session lifecycle.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ORM relationships.
    # owner: the User that owns the session.
    # history: all SearchHistory rows belonging to this session.
    owner: "User" = Relationship(back_populates="search_sessions")
    history: List["SearchHistory"] = Relationship(
        back_populates="session", cascade_delete=True
    )

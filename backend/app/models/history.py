from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
import uuid

from app.schemas.history import SearchHistoryBase

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.search_session import SearchSession

# -----------------------------------------------------------------------------
# Search history model
# -----------------------------------------------------------------------------

# Database model: maps to the `search_history` table.
# Represents one user query and the corresponding agent result inside a session.
class SearchHistory(SearchHistoryBase, table=True):
    """
    This is the durable, queryable source of truth for the full conversation —
    unlike SearchSession.memory, — used by admin dashboards, analytics, and anywhere per-turn detail/timestamps matter.
    """
    __tablename__ = "search_history"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Foreign key to the session where this query belongs.
    session_id: uuid.UUID = Field(
        foreign_key="search_session.id", nullable=False, ondelete="CASCADE"
    )
    # Foreign key to the user who made the query.
    # Keeping owner_id here makes it easier to filter a user's history directly.
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ORM relationships for navigation in Python code.
    session: "SearchSession" = Relationship(back_populates="history")
    owner: "User" = Relationship()
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.models.search_session import SearchSession
from app.schemas.user import UserBase

# -----------------------------------------------------------------------------
# SQLModel notes
# -----------------------------------------------------------------------------
# In this file we use SQLModel classes for:
#
# 1. Database models
#    Classes declared with `table=True`, for example `class User(..., table=True)`,
#    are mapped to real database tables. Their fields become table columns and
#    their `Relationship(...)` attributes describe ORM relationships.
# -----------------------------------------------------------------------------


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# User model
# -----------------------------------------------------------------------------

# Database model: this class maps to the `user` table because of `table=True`.
# It contains database-only fields such as `id`, `hashed_password`, timestamps,
# and ORM relationships. Notice that we store `hashed_password`, not the plain
# password received by UserCreate/UserRegister
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    # ORM relationships: these are not plain API fields.
    # They connect this user with the related rows in other tables.
    # `cascade_delete=True` means related records are deleted when the user is deleted.
    search_sessions: list["SearchSession"] = Relationship(
        back_populates="owner", cascade_delete=True
    )
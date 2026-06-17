"""
app/models/__init__.py

Import order matters here: SQLModel needs every model that participates in a
Relationship() to be imported and registered before any table is created or
any relationship is resolved. We import User first (no model dependencies),
then SearchSession (depends on User), then SearchHistory (depends on both).
"""
from app.models.user import User
from app.models.search_session import SearchSession
from app.models.history import SearchHistory

# Re-export schema Create types used by db.py / crud.py for the bootstrap superuser
from app.schemas.user import UserCreate, UserUpdate

__all__ = ["User", "SearchSession", "SearchHistory", "UserCreate", "UserUpdate"]
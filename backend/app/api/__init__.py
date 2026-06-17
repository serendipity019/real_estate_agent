from fastapi import APIRouter

from app.api.routers import (
    auth,
    private,
    users,
    utils,
    chat,
    health,
    knowledge,
    retrieval,
    sessions,
)
from app.core.config import get_settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(health.router)
api_router.include_router(sessions.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(retrieval.router)

settings = get_settings()

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
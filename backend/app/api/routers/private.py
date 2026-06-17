from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.depedencies import SessionDep
from app.core.security import get_password_hash
from app.schemas.user import UserPublic
from app.models.user import User

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_verified: bool = False


@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate, session: SessionDep) -> Any:
    """
    Create a new user. Local/dev environment only — see main.py wiring.
    """
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )

    session.add(user)
    session.commit()

    return user
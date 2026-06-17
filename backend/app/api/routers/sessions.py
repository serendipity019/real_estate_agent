"""
routers/sessions.py — CRUD for SearchSession (chat sessions).

A session must exist before /chat can be called against it. Users can only
see/manage their own sessions; superusers are not given blanket access here
(history/session content is personal — admin visibility, if ever needed,
should go through a dedicated audit endpoint, not by hijacking ownership checks).
"""

import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import select, func

from app.api.depedencies import SessionDep, CurrentUser
from app.models.search_session import SearchSession
from app.schemas.authentication_generic import Message
from app.schemas.history import SearchHistoriesPublic, SearchHistoryPublic
from app.schemas.search_session import ( 
    SearchSessionPublic, SearchSessionCreate,
    SearchSessionsPublic,  SearchSessionUpdate, )
from app.crud import create_search_session, get_history_for_session

router = APIRouter(prefix="/sessions", tags=["Chat Sessions"])

@router.post("/", response_model=SearchSessionPublic)
def create_session(*, session:SessionDep, 
                   current_user: CurrentUser, session_in:SearchSessionCreate)-> SearchSessionPublic:
    """Start a new chat session for the current user. """
    db_session = create_search_session(session=session, owner_id=current_user.id, title=session_in.title)
    return db_session


@router.get("/", response_model=SearchSessionsPublic)
def list_my_sessions(*, session:SessionDep, 
                     current_user:CurrentUser, skip: int = 0, limit: int = 10)-> SearchSessionsPublic:
    """List all chat sessions belonging to the current user."""
    count_statement = (
        select(func.count()).select_from(SearchSession).where(SearchSession.owner_id == current_user.id)
    ) 
    count = session.exec(count_statement).one()

    statement = (select(SearchSession).where(SearchSession.owner_id == current_user.id)
                 .order_by(-SearchSession.updated_at).offset(skip).limit(limit))
    sessions = session.exec(statement).all()

    return SearchSessionsPublic(
        data=[SearchSessionPublic.model_validate(s) for s in sessions], count=count
    )

@router.get("/{session_id}", response_model=SearchSessionPublic)
def get_session_by_id(*, session: SessionDep,
                      current_user: CurrentUser, session_id: uuid.UUID) -> SearchSessionPublic:
    """Get one chat session — must be owned by the current user."""
    db_session = session.get(SearchSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if db_session.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session. Access Denied")
    return db_session

@router.patch("/{session_id}", response_model=SearchSessionPublic)
def rename_session(*, session: SessionDep, current_user: CurrentUser,
                   session_id: uuid.UUID, session_in: SearchSessionUpdate,
) -> SearchSessionPublic:
    """Rename a chat session (e.g. give it a friendly title)."""
    db_session = session.get(SearchSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if db_session.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session. Access Denied")
    
    update_data = session_in.model_dump(exclude_unset=True)
    db_session.sqlmodel_update(update_data)
    session.add(db_session)
    session.commit()
    session.refresh(db_session)

    return db_session

@router.delete("/{session_id}", response_model=Message)
def delete_session(*, session: SessionDep, current_user: CurrentUser, session_id: uuid.UUID
                   ) -> Message :
    """Delete a chat session and all its history (cascade)."""
    db_session = session.get(SearchSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if db_session.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session. Access Denied")
    
    session.delete(db_session)
    session.commit()
    return Message(message=f"Session '{db_session.title}' deleted succesfully")

@router.get("/{session_id}/history", response_model=SearchHistoriesPublic)
def get_session_history(*,session: SessionDep,
    current_user: CurrentUser, session_id: uuid.UUID,
    skip: int = 0, limit: int = 100,
) -> SearchHistoriesPublic:
    """
    Return the full, durable turn-by-turn history for a session
    (reads SearchHistory rows — the detailed audit trail, not the memory cache).
    """
    db_session = session.get(SearchSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if db_session.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session. Access Denied")
    
    entries = get_history_for_session(
        session=session, session_id=session_id, skip=skip, limit=limit
    )
    return SearchHistoriesPublic(
        data=[SearchHistoryPublic.model_validate(e) for e in entries],
        count=len(entries),
    )

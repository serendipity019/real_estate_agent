"""
routers/chat.py — /chat endpoint: user message → LangGraph agent → response.

Session-based flow:
  1. Resolve the SearchSession (create one if no session_id given), verify ownership.
  2. Load prior turns from SearchSession.memory (fast-path JSON cache).
  3. Convert memory + new message into LangChain message objects.
  4. Invoke the compiled LangGraph with the full state.
  5. Extract the final AIMessage and any tool calls from the state.
  6. Persist: append the new turn to memory (capped, re-serialized) and
     insert a durable SearchHistory row.
  7. Return a structured ChatResponse.
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException

from langchain_core.messages import HumanMessage, AIMessage

from app.api.depedencies import SessionDep, CurrentUser
from app.models.search_session import SearchSession
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallInfo, ChatMessage
from app.agent.graph import build_graph
from app.crud import (
    create_search_session,
    load_memory,
    save_memory,
    create_history_entry
    )

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

def _resolve_session(
        *, db_session: SessionDep, current_user: CurrentUser, session_id: uuid.UUID | None
) -> SearchSession:
    """Load an existing session (verifying ownership) or create a new one."""
    if session_id is None:
        return create_search_session(session=db_session, owner_id=current_user.id)
    
    search_session = db_session.get(SearchSession, session_id)
    if not search_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if search_session.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session.")
    
    return search_session

def _memory_to_messages(turns: list[ChatMessage]) -> list:
    """Convert cached ChatMessage turns into LangChain message objects."""
    messages= []
    for turn in turns:
        if turn.role == 'user':
            messages.append(HumanMessage(content=turn.content))
        elif turn.role == "assistant":
            messages.append(AIMessage(content=turn.content))    
    return messages

def _extract_tools_used(all_messages: list) -> list[ToolCallInfo]:
    """Walk the message list and collect every tool that was called."""
    tools_used = []
    for msg in all_messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                args = tc.get("args", {})
                summary = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
                tools_used.append(
                    ToolCallInfo(tool_name=tc["name"], input_summary=summary)
                )    
    return tools_used


def _detect_model(all_messages: list) -> str:
    """Inspect the last AIMessage response_metadata to detect which model answered."""
    for msg in reversed(all_messages):
        if isinstance(msg, AIMessage):
            meta = getattr(msg, "response_metadata", {})
            model = meta.get("model") or meta.get("model_name", "")
            if model:
                return model
    return "unknown"


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db_session: SessionDep, current_user: CurrentUser) -> ChatResponse:
    """
    Send a message to the Smart Real Estate Assistant.

    Omit `session_id` to start a brand-new session — the response will
    include the generated `session_id` so the client can reuse it on the
    next turn. The server maintains conversation memory; no history array
    needs to be sent by the client.

    The agent will automatically:
    - Search the knowledge base for market data questions
    - Run the mortgage calculator for loan/payment questions
    - Combine both in a single answer when relevant

    Include `history` to maintain a multi-turn conversation.
    """
    try:
        search_session = _resolve_session(
            db_session=db_session,
            current_user=current_user,
            session_id=request.session_id,
        )

        prior_turns = load_memory(search_session)
        messages = _memory_to_messages(prior_turns) + [
            HumanMessage(content=request.message)
        ]

        logger.info(
            "Chat request [session=%s, user=%s]: %s",
            search_session.id,
            current_user.id,
            request.message[:80],
        )

        graph = build_graph()
        # Run the LangGraph — this loops agent ↔ tools until done
        final_state = graph.invoke({"messages": messages})
        all_messages = final_state["messages"]

        # The last message is always the agent's final AIMessage
        last_message = all_messages[-1]
        if not isinstance(last_message, AIMessage):
            raise ValueError("Unexpected final message type from graph.")

        reply_text = last_message.content
        tools_used = _extract_tools_used(all_messages)
        model_used = _detect_model(all_messages)

        # ── Persist: update fast-path memory cache ──────────────────────────────
        updated_turns = prior_turns + [
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=reply_text)
        ]
        save_memory(session=db_session, search_session=search_session, turns=updated_turns)

        # ── Persist: durable audit-trail row ─────────────────────────────────────
        create_history_entry(
            session=db_session,
            session_id=search_session.id,
            owner_id=current_user.id,
            query= request.message,
            result=reply_text,
        )

        logger.info(
            "Chat response [session=%s]: %d tool(s) used, model=%s",
            search_session.id,
            len(tools_used),
            model_used,
        )

        return ChatResponse(
            session_id=search_session.id,
            reply=reply_text,
            tools_used=tools_used,
            model_used=model_used,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

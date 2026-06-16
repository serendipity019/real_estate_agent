"""
routers/chat.py — /chat endpoint: user message → LangGraph agent → response.

Flow:
  1. Convert request history to LangChain HumanMessage / AIMessage objects
  2. Invoke the compiled LangGraph with the full state
  3. Extract the final AIMessage and any tool calls from the state
  4. Return a structured ChatResponse
"""
import logging
from fastapi import APIRouter, HTTPException

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.schemas.chat import ChatRequest, ChatResponse, ToolCallInfo
from app.agent.graph import build_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def _history_to_messages(request: ChatRequest) -> list:
    """Convert ChatRequest history + new message into LangChain message objects."""
    messages = []
    for turn in request.history:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        elif turn.role == "assistant":
            messages.append(AIMessage(content=turn.content))
    messages.append(HumanMessage(content=request.message))
    return messages


def _extract_tools_used(all_messages: list) -> list[ToolCallInfo]:
    """Walk the message list and collect every tool that was called."""
    tools_used = []
    for msg in all_messages:
        # AIMessage with tool_calls attached
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                # Summarise the input args concisely
                args = tc.get("args", {})
                summary = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3])
                tools_used.append(
                    ToolCallInfo(tool_name=tc["name"], input_summary=summary)
                )
    return tools_used


def _detect_model(all_messages: list) -> str:
    """
    Heuristic: inspect the last AIMessage response_metadata to detect which
    model actually produced the final answer.
    """
    for msg in reversed(all_messages):
        if isinstance(msg, AIMessage):
            meta = getattr(msg, "response_metadata", {})
            model = meta.get("model") or meta.get("model_name", "")
            if model:
                return model
    return "unknown"


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the Smart Real Estate Assistant.

    The agent will automatically:
    - Search the knowledge base for market data questions
    - Run the mortgage calculator for loan/payment questions
    - Combine both in a single answer when relevant

    Include `history` to maintain a multi-turn conversation.
    """
    try:
        graph = build_graph()
        messages = _history_to_messages(request)

        logger.info(
            "Chat request [session=%s]: %s", request.session_id, request.message[:80]
        )

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

        logger.info(
            "Chat response [session=%s]: %d tool(s) used, model=%s",
            request.session_id,
            len(tools_used),
            model_used,
        )

        return ChatResponse(
            reply=reply_text,
            tools_used=tools_used,
            model_used=model_used,
            session_id=request.session_id,
        )

    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

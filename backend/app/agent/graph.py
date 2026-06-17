"""
agent/graph.py — LangGraph StateGraph for the Smart Real Estate Assistant.

Graph topology:
    START → agent_node → should_continue?
                              ↓ YES (tool calls present)
                          tools_node → agent_node  (loop)
                              ↓ NO  (final answer)
                             END

The agent uses Claude Sonnet 4.6 as primary model.
If the Anthropic API fails, it automatically falls back to GPT-4o Mini.
"""
import logging
from functools import lru_cache
from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.core.config import get_settings
from app.tools import TOOLS

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Smart Real Estate Assistant specialising in the Greek property market.

You help users with two main tasks:
1. **Market insights** — answer questions about property prices, trends, and neighbourhoods
   across Athens and Greece. Always use the `search_knowledge_base` tool first when the
   user asks factual market questions. Cite your sources.

2. **Mortgage calculations** — compute monthly payments, total costs, and amortisation
   schedules. Use the `calculate_mortgage` tool whenever the user provides a loan amount,
   interest rate, or asks about affordability.

Guidelines:
- Be concise and professional, but friendly.
- When presenting mortgage results, format numbers clearly with the € symbol.
- If the knowledge base returns no results, say so honestly and offer general guidance.
- You may combine both tools in a single response (e.g. "Here are the market prices AND
  your estimated monthly payment for a property in that area.").
- Always respond in the same language the user writes in (Greek or English).
"""


# ── Agent state ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """The state that flows through every node of the LangGraph."""
    messages: Annotated[list[BaseMessage], add_messages]


# ── Model factory ──────────────────────────────────────────────────────────────

def _build_primary_model():
    settings = get_settings()
    return ChatAnthropic(
        model=settings.PRIMARY_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=2048,
    ).bind_tools(TOOLS)


def _build_fallback_model():
    settings = get_settings()
    return ChatOpenAI(
        model=settings.FALLBACK_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.0,
        max_tokens=2048,
    ).bind_tools(TOOLS)


# ── Nodes ──────────────────────────────────────────────────────────────────────

def agent_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    The 'brain' node — calls the LLM with the full message history.
    Tries Claude Sonnet 4.6; falls back to GPT-4o Mini on any exception.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    try:
        logger.info("Agent node: calling primary model (Claude Sonnet 4.6).")
        response = _build_primary_model().invoke(messages, config)
    except Exception as primary_exc:
        logger.warning(
            "Primary model failed (%s). Falling back to GPT-4o Mini.", primary_exc
        )
        try:
            response = _build_fallback_model().invoke(messages, config)
        except Exception as fallback_exc:
            logger.error("Fallback model also failed: %s", fallback_exc)
            raise fallback_exc

    return {"messages": [response]}


# ── Routing logic ──────────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    """
    Edge function: if the last message contains tool_calls → run tools.
    Otherwise → we're done, go to END.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ── Graph creation ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def build_graph():
    """
    Compile and return the LangGraph StateGraph.
    Cached so the graph is only compiled once per process.
    """
    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # Edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")   # after tools, always loop back to agent

    compiled = graph.compile()
    logger.info("LangGraph compiled successfully.")
    return compiled

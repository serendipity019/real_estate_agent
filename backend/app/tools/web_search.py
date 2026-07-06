"""
tools/web_search_tool.py — LangChain @tool that uses Tavily Search API
for real-time web searches about the Greek real estate market.

Use this for anything time-sensitive that isn't in the ChromaDB knowledge base:
current news, new legislation, recent price trends, Golden Visa rule changes, etc.
"""

import os 
import json
import logging
from typing import Any

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.TAVILY_API_KEY:
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY

_tavily_search = TavilySearch(
    max_results=3,
    topic="general",
    include_answer=True,
    include_raw_content=False,
    include_images=False,
)

@tool
def web_search(query: str) -> str:
    """
    Search the web for current Greek real estate market news, legislation,
       and information NOT available in the local knowledge base.

    Use this tool for: 
       - Fresh or external information about the real estate in Greece is needed and don't exist in our knowledge base.
       - Recent market reports or statistics you don't have data for.
       - Goverment announcements about Golden Visa.
       - Bank interest rates for mortgages.

    Recommended sources:
       - Some useful relative with the real estate rent and sold prices sites to use are: [Spitogatos](https://www.spitogatos.gr/), [Xrysi eukairia](https://www.xe.gr/) 
       - Some goverment sites that maybe contain usefull info are: [The site of the goverment](https://www.government.gov.gr/), [The site of the finance minister](https://minfin.gov.gr/). 
       - Maybe is useful to have and this in your mind: [Gate for Greek Database and Services](https://data.gov.gr/).

    Do NOT USE this:
       - For objective zone prices (use get_objective_zone_price instead) or for mortagage calculations (use calculate_mortgage instead).
       - For unrelative to the Greek real estate questions. Instead suggest the user to use [ChatGPT](https://chatgpt.com/) or [Claude](https://claude.ai/new) if they want to ask unrelative questions.   

    Args:
        query: Search query in Greek or English, e.g.
               "αντικειμενικές αξίες ακινήτων 2025 αλλαγές" or
               "Greece real estate market trends Q3 2025"

    Returns:
        Summarized search results with sources.
    """

    if not query or not query.strip():
        logger.error("No query provided")
        return json.dumps(
            {"error": "No query provided"},
            ensure_ascii=False,
        )
    logger.info("Tavily web search: %s", query)

    try:
        results: Any = _tavily_search.invoke({"query": query})
        if not results:
            return f"Do not found results for the: '{query}'"
        
        lines = [f"**Search results for: ** '{query}'", ""]
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            content = r.get("content", "").strip()
            if content:
                lines.append(f"**{i}.** {content[:400]}")
                if url:
                    lines.append(f"   _Source: {url}_")
                lines.append("")

        return json.dumps(
            "\n".join(lines),
            ensure_ascii=False,
            default=str,
        )
    
    except Exception as exc:
        logger.exception("Tavily search failed.")
        return json.dumps(
            {"error": "Tavily search failed",
             "details": str(exc)},
             ensure_ascii=False
        )

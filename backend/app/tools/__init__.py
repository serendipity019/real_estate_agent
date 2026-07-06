from app.tools.mortgage_calculator import calculate_mortgage
from app.tools.retriever import search_knowledge_base
from app.tools.web_search import web_search

TOOLS = [search_knowledge_base, calculate_mortgage, web_search]

__all__ = ["calculate_mortgage", "search_knowledge_base", "web_search", "TOOLS"]
"""
tools/retriever_tool.py — LangChain tool that searches the ChromaDB knowledge base.

The agent calls this whenever the user asks about Greek real estate market data,
neighbourhood prices, trends, legal info, or anything stored in the knowledge base.
"""
from langchain_core.tools import tool
from app.rag.pipeline import get_pipeline


@tool
def search_knowledge_base(query: str, category: str = "") -> str:
    """
    Search the Greek real estate knowledge base for relevant market information.

    Use this tool whenever the user asks about:
    - Property prices in specific areas of Athens or Greece
    - Real estate market trends, statistics, or reports
    - Neighbourhood comparisons (Kolonaki, Glyfada, Piraeus, etc.)
    - Legal or tax aspects of buying property in Greece
    - Any factual question about the Greek property market

    Args:
        query: Natural-language search query describing what information is needed.
        category: Optional filter — one of: 'market_data', 'neighborhood', 'legal', 'general'.
                  Leave empty to search across all categories.

    Returns:
        Formatted context string with the most relevant passages from the knowledge base,
        including source and relevance score for each passage.
        Returns a clear message if no relevant information is found.
    """
    pipeline = get_pipeline()

    if pipeline.count() == 0:
        return (
            "The knowledge base is currently empty. "
            "No real estate documents have been ingested yet. "
            "Please inform the user and give a polite answer that our knowledge base don't contain relative data."
        )

    chunks = pipeline.retrieve(
        query=query,
        category_filter=category if category else None,
    )

    if not chunks:
        return (
            f"No relevant information found in the knowledge base for: '{query}'. "
            "Asking the user for more context or give a polite answer that our knowledge base don't contain relative data."
        )

    return pipeline.build_context(chunks)

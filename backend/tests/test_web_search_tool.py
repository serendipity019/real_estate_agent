"""
tests/test_web_search.py - Unit tests fo the Tavily web search tool. All HTTP calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.tools.web_search import web_search

@pytest.fixture
def mock_tavily():
    """Fixture that provides a mocked Tavily search instance with automatic patching."""
    mock = MagicMock()
    with patch("app.tools.web_search._tavily_search", mock):
        yield mock
    # Patch is automatically cleaned up after test


@pytest.fixture
def parse_result():
    """Fixture that provides a helper to parse JSON results."""
    def _parse(result: str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    return _parse

class TestTavilyTool:
    """Test suite for the Tavily web search tool."""

    def test_search_returns_formatted_results(self):
        """Test that web search returns properly formatted results."""
        mock_tavily.invoke.return_value = [
            {"url": "https://example.gr/news", "content": "Αύξηση τιμών 10% στην Αθήνα το Q3 2025."},
            {"url": "https://other.gr/article", "content": "Η Θεσσαλονίκη ανεβαίνει 9,6% σε ετήσια βάση."},
        ]

        result = web_search.invoke({"query": "τιμές ακινήτων Αθήνα 2025"})
        parsed_result = parse_result(result)

        assert "Αύξηση τιμών" in parsed_result
        assert "example.gr" in parsed_result
        assert "Θεσσαλονίκη" in parsed_result

    def test_search_no_api_key_returns_graceful_message(self):
        """Test that missing API key returns appropriate message."""
        result = web_search.invoke({"query": "anything"})

        assert result == "Web search is unavailable."

    def test_search_empty_results_returns_message(self):
        """Test handling of empty search results."""
        mock_tavily.invoke.return_value = []

        result = web_search.invoke({"query": "very obscure query"})

        assert "Do not found results" in result
        assert "very obscure query" in result

    def test_search_api_exception_returns_graceful_message(self):
        """Test handling of API exceptions."""
        mock_tavily.invoke.side_effect = RuntimeError("API timeout")

        result = web_search.invoke({"query": "anything"})

        parsed_result = parse_result(result)
            
        assert "error" in parsed_result
        assert "Tavily search failed" in parsed_result["error"]
        assert "API timeout" in parsed_result["details"]

    def test_empty_query_returns_error(self):
        """Test that empty query returns appropriate error."""
        
        result = web_search.invoke({"query": ""})
            
        # Parse the JSON error response
        parsed_result = parse_result(result)
            
        assert "error" in parsed_result
        assert parsed_result["error"] == "No query provided"

    def test_whitespace_query_returns_error(self):
        """Test that whitespace-only query returns appropriate error."""
        
        result = web_search.invoke({"query": "   "})
            
        # Parse the JSON error response
        parsed_result = parse_result(result)
            
        assert "error" in parsed_result
        assert parsed_result["error"] == "No query provided"

"""
tests/test_chat.py — /chat endpoint tests (session resolution, memory, history persistence).

The LangGraph agent (build_graph) is mocked throughout — these tests verify the
session/memory/history plumbing, not real LLM behavior (covered separately
in test_mortgage_calculator.py and the Phase 2 agent unit tests).
"""
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage


def _make_graph(reply="The average price in Kolonaki is €4,500/m².", with_tool_call=False):
    graph = MagicMock()
    if with_tool_call:
        tool_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search_knowledge_base", "args": {"query": "Kolonaki"}, "id": "tc1"}],
            response_metadata={"model": "claude-sonnet-4-6"},
        )
        final_msg = AIMessage(content=reply, response_metadata={"model": "claude-sonnet-4-6"})
        graph.invoke.return_value = {"messages": [tool_msg, final_msg]}
    else:
        graph.invoke.return_value = {
            "messages": [AIMessage(content=reply, response_metadata={"model": "claude-sonnet-4-6"})]
        }
    return graph


def test_chat_creates_new_session_when_none_given(client, normal_user_token_headers):
    graph = _make_graph()
    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp = client.post(
            "/chat", json={"message": "What are property prices in Kolonaki?"},
            headers=normal_user_token_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "Kolonaki" in data["reply"]
    assert data["tools_used"] == []


def test_chat_reuses_existing_session(client, normal_user_token_headers):
    graph = _make_graph()

    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp1 = client.post(
            "/chat", json={"message": "Tell me about Kolonaki."},
            headers=normal_user_token_headers,
        )
    session_id = resp1.json()["session_id"]

    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp2 = client.post(
            "/chat",
            json={"message": "And what about Glyfada?", "session_id": session_id},
            headers=normal_user_token_headers,
        )
    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == session_id

    second_call_messages = graph.invoke.call_args[0][0]["messages"]
    assert len(second_call_messages) == 3  # user1, assistant1, user2


def test_chat_persists_history_row(client, normal_user_token_headers):
    graph = _make_graph(reply="Kolonaki averages €4,500/m².")
    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp = client.post(
            "/chat", json={"message": "Kolonaki prices?"},
            headers=normal_user_token_headers,
        )
    session_id = resp.json()["session_id"]

    history_resp = client.get(
        f"/sessions/{session_id}/history", headers=normal_user_token_headers
    )
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert history_data["count"] == 1
    assert history_data["data"][0]["query"] == "Kolonaki prices?"
    assert "4,500" in history_data["data"][0]["result"]


def test_chat_updates_session_memory(client, normal_user_token_headers):
    graph = _make_graph(reply="Sure, here's the info.")
    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp = client.post(
            "/chat", json={"message": "Hello"}, headers=normal_user_token_headers
        )
    session_id = resp.json()["session_id"]

    with patch("app.api.routers.chat.build_graph", return_value=graph):
        client.post(
            "/chat",
            json={"message": "Follow-up", "session_id": session_id},
            headers=normal_user_token_headers,
        )
    messages = graph.invoke.call_args[0][0]["messages"]
    assert len(messages) == 3  # prior user+assistant + new user message


def test_chat_with_tool_calls_reports_tools_used(client, normal_user_token_headers):
    graph = _make_graph(with_tool_call=True)
    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp = client.post(
            "/chat", json={"message": "Kolonaki market data"},
            headers=normal_user_token_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tools_used"]) == 1
    assert data["tools_used"][0]["tool_name"] == "search_knowledge_base"


def test_chat_nonexistent_session_404(client, normal_user_token_headers):
    graph = _make_graph()
    fake_id = "00000000-0000-0000-0000-000000000000"
    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp = client.post(
            "/chat",
            json={"message": "Hi", "session_id": fake_id},
            headers=normal_user_token_headers,
        )
    assert resp.status_code == 404


def test_chat_cannot_use_another_users_session(client, normal_user_token_headers):
    graph = _make_graph()

    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp1 = client.post(
            "/chat", json={"message": "Hi"}, headers=normal_user_token_headers
        )
    session_id = resp1.json()["session_id"]

    client.post(
        "/users/signup",
        json={"email": "intruder@example.com", "password": "intruderpass123"},
    )
    login_resp = client.post(
        "/login/access-token",
        data={"username": "intruder@example.com", "password": "intruderpass123"},
    )
    intruder_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    with patch("app.api.routers.chat.build_graph", return_value=graph):
        resp2 = client.post(
            "/chat",
            json={"message": "Hijack attempt", "session_id": session_id},
            headers=intruder_headers,
        )
    assert resp2.status_code == 403


def test_chat_requires_auth(client):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 401


def test_chat_empty_message_rejected(client, normal_user_token_headers):
    resp = client.post("/chat", json={"message": ""}, headers=normal_user_token_headers)
    assert resp.status_code == 422


def test_chat_graph_error_returns_500(client, normal_user_token_headers):
    broken_graph = MagicMock()
    broken_graph.invoke.side_effect = RuntimeError("LLM unavailable")
    with patch("app.api.routers.chat.build_graph", return_value=broken_graph):
        resp = client.post(
            "/chat", json={"message": "Hello"}, headers=normal_user_token_headers
        )
    assert resp.status_code == 500

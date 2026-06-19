"""
tests/test_ui.py — Tests for app/ui/api_client.py and the Gradio callback
functions in app/ui/gradio_app.py.

api_client functions are tested by mocking httpx.Client; the Gradio callbacks
are tested by mocking the api_client module functions they call, since the
callbacks themselves contain the business logic we care about (not Gradio's
rendering, which isn't ours to test).
"""
from unittest.mock import MagicMock, patch
import pytest

from app.ui import api_client as api
from app.ui import gradio_app as ui


# ── api_client tests ─────────────────────────────────────────────────────────

def test_login_success_returns_token():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"access_token": "abc123", "token_type": "bearer"}
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_resp
        token = api.login("user@example.com", "password123")
    assert token == "abc123"


def test_login_failure_raises_api_error():
    mock_resp = MagicMock(status_code=401)
    mock_resp.json.return_value = {"detail": "Incorrect email or password"}
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_resp
        with pytest.raises(api.APIError) as exc_info:
            api.login("user@example.com", "wrongpass")
    assert exc_info.value.status_code == 401
    assert "Incorrect email" in exc_info.value.detail


def test_signup_success():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"id": "u1", "email": "new@example.com"}
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_resp
        result = api.signup("new@example.com", "password123")
    assert result["email"] == "new@example.com"


def test_list_sessions_returns_data_list():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"data": [{"id": "s1", "title": "Test"}], "count": 1}
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
        sessions = api.list_sessions("token123")
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Test"


def test_send_message_includes_session_id_when_present():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "session_id": "s1", "reply": "Hello!", "tools_used": [], "model_used": "claude"
    }
    with patch("httpx.Client") as MockClient:
        mock_post = MockClient.return_value.__enter__.return_value.post
        mock_post.return_value = mock_resp
        api.send_message("token123", "Hi", session_id="s1")
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["session_id"] == "s1"


def test_send_message_omits_session_id_when_none():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "session_id": "new1", "reply": "Hi!", "tools_used": [], "model_used": "claude"
    }
    with patch("httpx.Client") as MockClient:
        mock_post = MockClient.return_value.__enter__.return_value.post
        mock_post.return_value = mock_resp
        api.send_message("token123", "Hi")
    call_kwargs = mock_post.call_args
    assert "session_id" not in call_kwargs.kwargs["json"]


def test_api_error_falls_back_to_raw_text_on_non_json():
    mock_resp = MagicMock(status_code=500)
    mock_resp.json.side_effect = ValueError("not json")
    mock_resp.text = "Internal Server Error"
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(api.APIError) as exc_info:
            api.list_sessions("token123")
    assert "Internal Server Error" in exc_info.value.detail


# ── gradio_app callback tests ────────────────────────────────────────────────

def test_session_choices_format():
    sessions = [{"id": "s1", "title": "Kolonaki"}, {"id": "s2", "title": "Glyfada"}]
    choices = ui._session_choices(sessions)
    assert choices == [("Kolonaki", "s1"), ("Glyfada", "s2")]


def test_history_to_chatbot_format():
    rows = [
        {"query": "Hi", "result": "Hello!"},
        {"query": "Prices?", "result": None},
    ]
    messages = ui._history_to_chatbot(rows)
    assert messages == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Prices?"},
    ]


def test_do_login_success():
    with patch.object(ui.api, "login", return_value="tok123"), \
         patch.object(ui.api, "get_current_user", return_value={"email": "a@b.com"}), \
         patch.object(ui.api, "list_sessions", return_value=[]):
        result = ui.do_login("a@b.com", "password123")
    token = result[1]
    user = result[2]
    assert token == "tok123"
    assert user["email"] == "a@b.com"


def test_do_login_missing_fields():
    result = ui.do_login("", "")
    assert result[1] is None


def test_do_login_api_error():
    with patch.object(ui.api, "login", side_effect=api.APIError(401, "bad creds")):
        result = ui.do_login("a@b.com", "wrongpass")
    assert result[1] is None


def test_on_send_message_success():
    with patch.object(
        ui.api, "send_message",
        return_value={"session_id": "s1", "reply": "Hi there!", "tools_used": [], "model_used": "claude"},
    ), patch.object(ui.api, "list_sessions", return_value=[]):
        chat_history, msg, sid, sessions = ui.on_send_message("tok", None, "Hello", [])
    assert chat_history[-1]["content"] == "Hi there!"
    assert chat_history[-1]["role"] == "assistant"
    assert sid == "s1"
    assert msg == ""


def test_on_send_message_empty_input_noop():
    chat_history, msg, sid, sessions = ui.on_send_message(
        "tok", "s1", "   ", [{"role": "user", "content": "prev"}]
    )
    assert len(chat_history) == 1
    assert sid == "s1"


def test_on_send_message_no_token_noop():
    chat_history, msg, sid, sessions = ui.on_send_message(None, None, "Hello", [])
    assert chat_history == []
    assert sessions == []


def test_on_send_message_api_error_shows_warning():
    with patch.object(ui.api, "send_message", side_effect=api.APIError(500, "LLM down")):
        chat_history, msg, sid, sessions = ui.on_send_message("tok", "s1", "Hello", [])
    assert "⚠️" in chat_history[-1]["content"]
    assert "LLM down" in chat_history[-1]["content"]

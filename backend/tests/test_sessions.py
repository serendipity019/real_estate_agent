"""
tests/test_sessions.py — /sessions endpoint tests (create/list/get/rename/delete/history).
"""


def test_create_session(client, normal_user_token_headers):
    resp = client.post(
        "/sessions/",
        json={"title": "Kolonaki research"},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Kolonaki research"
    assert "id" in data


def test_create_session_default_title(client, normal_user_token_headers):
    resp = client.post("/sessions/", json={}, headers=normal_user_token_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Untitled Search"


def test_list_my_sessions(client, normal_user_token_headers):
    client.post("/sessions/", json={"title": "Session A"}, headers=normal_user_token_headers)
    client.post("/sessions/", json={"title": "Session B"}, headers=normal_user_token_headers)

    resp = client.get("/sessions/", headers=normal_user_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 2


def test_get_session_by_id(client, normal_user_token_headers):
    create_resp = client.post(
        "/sessions/", json={"title": "Test session"}, headers=normal_user_token_headers
    )
    session_id = create_resp.json()["id"]

    resp = client.get(f"/sessions/{session_id}", headers=normal_user_token_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id


def test_get_nonexistent_session_404(client, normal_user_token_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/sessions/{fake_id}", headers=normal_user_token_headers)
    assert resp.status_code == 404


def test_rename_session(client, normal_user_token_headers):
    create_resp = client.post(
        "/sessions/", json={"title": "Old title"}, headers=normal_user_token_headers
    )
    session_id = create_resp.json()["id"]

    resp = client.patch(
        f"/sessions/{session_id}",
        json={"title": "New title"},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


def test_delete_session(client, normal_user_token_headers):
    create_resp = client.post(
        "/sessions/", json={"title": "To delete"}, headers=normal_user_token_headers
    )
    session_id = create_resp.json()["id"]

    resp = client.delete(f"/sessions/{session_id}", headers=normal_user_token_headers)
    assert resp.status_code == 200

    # Subsequent GET should 404
    get_resp = client.get(f"/sessions/{session_id}", headers=normal_user_token_headers)
    assert get_resp.status_code == 404


def test_cannot_access_another_users_session(client, normal_user_token_headers):
    # Create a second user
    client.post(
        "/users/signup",
        json={"email": "other.user@example.com", "password": "otherpass123"},
    )
    login_resp = client.post(
        "/login/access-token",
        data={"username": "other.user@example.com", "password": "otherpass123"},
    )
    other_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # First user creates a session
    create_resp = client.post(
        "/sessions/", json={"title": "Private"}, headers=normal_user_token_headers
    )
    session_id = create_resp.json()["id"]

    # Second user tries to access it
    resp = client.get(f"/sessions/{session_id}", headers=other_headers)
    assert resp.status_code == 403


def test_session_history_empty_initially(client, normal_user_token_headers):
    create_resp = client.post(
        "/sessions/", json={"title": "Fresh session"}, headers=normal_user_token_headers
    )
    session_id = create_resp.json()["id"]

    resp = client.get(f"/sessions/{session_id}/history", headers=normal_user_token_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_sessions_require_auth(client):
    resp = client.get("/sessions/")
    assert resp.status_code == 401

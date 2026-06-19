"""
tests/test_auth.py — Login, signup, and user management endpoint tests.
"""


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Smart Real Estate Assistant" in resp.json()["message"]


def test_login_with_bootstrapped_superuser(client, superuser_token_headers):
    assert "Authorization" in superuser_token_headers


def test_login_wrong_password_rejected(client):
    from app.core.config import get_settings
    settings = get_settings()
    resp = client.post(
        "/login/access-token",
        data={"username": settings.FIRST_SUPERUSER, "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_signup_new_user(client):
    resp = client.post(
        "/users/signup",
        json={"email": "newuser@example.com", "password": "securepass123", "full_name": "New User"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert "hashed_password" not in data  # never leak the hash


def test_signup_duplicate_email_rejected(client):
    client.post(
        "/users/signup",
        json={"email": "dupe@example.com", "password": "securepass123"},
    )
    resp = client.post(
        "/users/signup",
        json={"email": "dupe@example.com", "password": "anotherpass123"},
    )
    assert resp.status_code == 400


def test_read_current_user(client, normal_user_token_headers):
    resp = client.get("/users/me", headers=normal_user_token_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "regular.user@example.com"


def test_regular_user_cannot_list_all_users(client, normal_user_token_headers):
    resp = client.get("/users/", headers=normal_user_token_headers)
    assert resp.status_code == 403


def test_superuser_can_list_all_users(client, superuser_token_headers):
    resp = client.get("/users/", headers=superuser_token_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_unauthenticated_request_rejected(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401

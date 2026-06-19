"""
ui/api_client.py — This HTTP client the Gradio UI uses to talk to our own
FastAPI backend. Deliberately goes over HTTP (not direct Python calls) so the
UI behaves like any other API consumer.
"""
import httpx
from app.core.config import settings

# Mounted at /ui on the same FastAPI app, so we can always reach the API at
# the local loopback regardless of what host/port the server is bound to.
BASE_URL = f"http://127.0.0.1:{settings.APP_PORT}"

TIMEOUT = httpx.Timeout(60.0, connect=10.0)  # chat calls can be slow (LLM latency)

# ---------------Helping section --------------
class APIError(Exception):
    """Raised when the backend returns a non-2.. response, carries the detail message."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")

def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(resp.status_code, str(detail))
        
def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --------------Auth----------------------------

def login(email: str, password: str) -> str:
    """Returns the access token on success, raises APIError on failure."""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{BASE_URL}/login/access-token",
            data= {"username": email, "password": password}
        )
        _raise_for_status(resp)
        return resp.json()["access_token"]
    
def signup(email:str, password: str, full_name: str = "") -> dict:
    """Returns the created user's public data, raises APIError on failure."""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{BASE_URL}/users/signup",
            json={"email": email, "password": password, "full_name": full_name or None}
        )
        _raise_for_status(resp)
        return resp.json()
    
def get_current_user(token: str) -> list[dict]:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(f"{BASE_URL}/users/me", headers=_auth_headers(token))
        _raise_for_status(resp)
        return resp.json()
    
#---------------Sessions------------------------------------

def list_sessions(token: str) -> list[dict]:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(f"{BASE_URL}/sessions/", headers=_auth_headers(token=token))
        _raise_for_status(resp)
        return resp.json()["data"]

def create_session(token: str, title: str = "Untitled Search") -> dict:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{BASE_URL}/sessions/", json={"title": title}, headers=_auth_headers(token)
        )
        _raise_for_status(resp)
        return resp.json()
    
def rename_session(token: str, session_id: str, title: str) -> dict:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.patch(
            f"{BASE_URL}/sessions/{session_id}",
            json={"title": title},
            headers=_auth_headers(token)
        )
        _raise_for_status(resp)
        return resp.json()
    
def delete(token: str, session_id: str) -> None:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.delete(
            f"{BASE_URL}/sessions/{session_id}",
            headers=_auth_headers(token)
        )
        _raise_for_status(resp)
    
def get_session_history(token: str, session_id: str) -> list[dict]:
    """Returns the durable turn-by-turn history for a session, oldest first."""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(
            f"{BASE_URL}/sessions/{session_id}/history", headers=_auth_headers(token)
        )
        _raise_for_status(resp)
        return resp.json()["data"]
    
#------------Chat------------------------------------------------

def send_message(token: str, message: str, session_id: str | None = None) -> dict:
    """
    Send a chat message. Omit session_id to start a new session — the
    response's session_id should be captured by the caller for subsequent turns.
    """
    payload: dict = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{BASE_URL}/chat", json=payload, headers=_auth_headers(token) 
        )
        _raise_for_status(resp)
        return resp.json()
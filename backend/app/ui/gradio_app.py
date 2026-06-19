"""
ui/gradio_app.py — Gradio Blocks UI for the Smart Real Estate Assistant.

Layout:
  - Logged out: Login / Signup tabs
  - Logged in: sidebar (session list, new/rename/delete) + chat panel

State is held per-browser-session via gr.State (token, current user, active
session_id, and the loaded chat history) — never as module-level globals, so
concurrent users on the same server process never see each other's data.
"""

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

from app.ui import api_client as api

#--------Helpers----------------------

def _session_choices(sessions: list[dict]) -> list[tuple[str, str]]:
    """Build (label, value) pairs for the session radio/dropdown."""
    return [(s["title"], s["id"]) for s in sessions]

def _history_to_chatbot(history_rows: list[dict]) -> list[dict]:
    """Convert SearchHistory rows into Gradio Chatbot 'messages' format."""
    messages = []
    for row in history_rows:
        messages.append({"role": "user", "content": row["query"]})
        if row.get("result"):
            messages.append({"role": "assistant", "content": row["result"]})
    return messages

#----------------Auth callbacks---------------------------
def do_login(email: str, password: str)-> list:
    if not email or not password:
        return(
            gr.update(value="Please enter both email and password.", visible=True),
            None, None, gr.update(visible=True), gr.update(visible=False),
            [], None, [],
        )
    try:
        token = api.login(email, password)
        user = api.get_current_user(token)
        sessions = api.list_sessions(token)
    except api.APIError as e:
        return(
            gr.update(value=f"Login failed: {e.detail}", visible=True),
            None, None, gr.update(visible=True), gr.update(visible=False),
            [], None, [],
        )
    
    return(
        gr.update(value="", visible=False),
        token, user,
        gr.update(visible=False), gr.update(visible=True),
        sessions, None, []
    )

def do_signup(email: str, password: str, full_name: str):
    if not email or not password:
        return gr.update(value="Email and password are required.", visible=True)
    
    try:
        api.signup(email, password, full_name)
    except api.APIError as e:
        return gr.update(value=f"Signup failed: {e.detail}", visible=True)
    
    return gr.update(
        value="Account created! Please switch to the login tab to sign in.", visible=True
    )

def do_logout():
    return(
        None, None,
        gr.update(visible=True), gr.update(visible=False),
        [], None, [],
        gr.update(value=""), gr.update(value="")
    )

# ----- Session management callbacks ------------

def refresh_sessions(token: str):
    if not token:
        return [], None
    sessions = api.list_sessions(token)
    return sessions, None

def on_new_session(token: str):
    if not token:
        return [], None, []
    new_session = api.create_session(token)
    sessions = api.list_sessions(token)
    return sessions, new_session["id"], []

def on_select_session(token: str, session_id: str):
    if not token or not session_id:
        return []
    history_rows = api.get_session_history(token, session_id)
    return _history_to_chatbot(history_rows)

def on_rename_session(token: str, session_id: str, new_title: str):
    if not token or not session_id or not new_title:
        sessions = api.list_sessions(token) if token else []
        return sessions, gr.update(value="")
    api.rename_session(token, session_id, new_title)
    sessions = api.list_sessions(token)
    return sessions, gr.update(value="")

def on_delete_session(token: str, session_id: str):
    if not token or not session_id:
        sessions = api.list_sessions(token) if token else []
        return sessions, None, []
    api.delete_session(token, session_id)
    sessions = api.list_sessions(token)
    return sessions, None, []

# ----- Chat callback ---------------------------------

def on_send_message(token: str, session_id, message: str, chat_history: list):
    if not token:
        return chat_history, "", session_id, []
    if not message or not message.strip():
        return chat_history, "", session_id, []

    chat_history = chat_history + [{"role": "user", "content": message}]

    try:
        result = api.send_message(token, message, session_id)
        print("=" * 50)
        print("DEBUG: Full response from API:")
        print(result)
        print("=" * 50)
    except api.APIError as e:
        chat_history = chat_history + [
            {"role": "assistant", "content": f"⚠️ Error: {e.detail}"}
        ]
        return chat_history, "", session_id, []

    chat_history = chat_history + [{"role": "assistant", "content": result["reply"]}]
    new_session_id = result["session_id"]
    sessions = api.list_sessions(token)

    return chat_history, "", new_session_id, sessions

# ------- Build the components of the app------------------------------

def build_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="Smart Real Estate Assistant") as my_app:
        # ----- Per-browser-session state --------------------------------
        token_state = gr.State(None)
        user_state = gr.State(None)
        session_id_state = gr.State(None)
        sessions_state = gr.State([])

        gr.Markdown(
            "# 🏠 Smart Real Estate Assistant\n"
            "Greek real estate market insights & mortgage calculations."
        )

        # ---------- Logged-out view -------------------------------------------------
        with gr.Column(visible=True) as logged_out_view:
            with gr.Tabs():
                with gr.Tab("Login"):
                    login_email = gr.Textbox(label="Email")
                    login_password = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Log in", variant="primary")
                    login_error = gr.Markdown(visible=False)

                with gr.Tab("Sign up"):
                    signup_email = gr.Textbox(label="Email")
                    signup_password = gr.Textbox(label="Password", type="password")
                    signup_name = gr.Textbox(label="Full name (optional)")
                    signup_btn = gr.Button("Create account", variant="primary")
                    signup_message = gr.Markdown(visible=False)

        # ---- Logged-in view -----------------------------------------------------
        with gr.Column(visible=False) as logged_in_view:
            with gr.Row():
                welcome_text = gr.Markdown()
                logout_btn = gr.Button("Log out", scale=0)

            with gr.Row():
                # Sidebar: session list + management
                with gr.Column(scale=1):
                    gr.Markdown("### Your conversations")
                    new_session_btn = gr.Button("➕ New chat")
                    session_radio = gr.Radio(
                        choices=[], label="Sessions", interactive=True
                    )
                    rename_title = gr.Textbox(
                        label="Rename selected session", placeholder="New title…"
                    )
                    with gr.Row():
                        rename_btn = gr.Button("Rename")
                        delete_btn = gr.Button("Delete", variant="stop")

                # Main panel: chat
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(label="Chat", type="messages", height=480)
                    msg_box = gr.Textbox(
                        label="Message",
                        placeholder="Ask about Athens property prices or mortgage calculations…",
                    )
                    send_btn = gr.Button("Send", variant="primary")

        # ---- Wiring: Auth ----------------------------------------------------------
        login_btn.click(
            do_login,
            inputs=[login_email, login_password],
            outputs=[
                login_error, token_state, user_state,
                logged_out_view, logged_in_view,
                sessions_state, session_id_state, chatbot,
            ],
        ).then(
            lambda u: f"Logged in as **{u['email']}**" if u else "",
            inputs=[user_state],
            outputs=[welcome_text],
        ).then(
            lambda s: gr.update(choices=_session_choices(s)),
            inputs=[sessions_state],
            outputs=[session_radio],
        )

        signup_btn.click(
            do_signup,
            inputs=[signup_email, signup_password, signup_name],
            outputs=[signup_message],
        )

        logout_btn.click(
            do_logout,
            outputs=[
                token_state, user_state,
                logged_out_view, logged_in_view,
                sessions_state, session_id_state, chatbot,
                login_email, login_password,
            ],
        )

        # --- Wiring: Sessions ----------------------------------------
        new_session_btn.click(
            on_new_session,
            inputs=[token_state],
            outputs=[sessions_state, session_id_state, chatbot],
        ).then(
            lambda s, sid: gr.update(choices=_session_choices(s), value=sid),
            inputs=[sessions_state, session_id_state],
            outputs=[session_radio],
        )

        session_radio.change(
            on_select_session,
            inputs=[token_state, session_radio],
            outputs=[chatbot],
        ).then(
            lambda sid: sid,
            inputs=[session_radio],
            outputs=[session_id_state],
        )

        rename_btn.click(
            on_rename_session,
            inputs=[token_state, session_radio, rename_title],
            outputs=[sessions_state, rename_title],
        ).then(
            lambda s, sid: gr.update(choices=_session_choices(s), value=sid),
            inputs=[sessions_state, session_radio],
            outputs=[session_radio],
        )

        delete_btn.click(
            on_delete_session,
            inputs=[token_state, session_radio],
            outputs=[sessions_state, session_id_state, chatbot],
        ).then(
            lambda s: gr.update(choices=_session_choices(s), value=None),
            inputs=[sessions_state],
            outputs=[session_radio],
        )

        # --- Wiring: Chat ---------------------------------------------
        send_btn.click(
            on_send_message,
            inputs=[token_state, session_id_state, msg_box, chatbot],
            outputs=[chatbot, msg_box, session_id_state, sessions_state],
        ).then(
            lambda s, sid: gr.update(choices=_session_choices(s), value=sid),
            inputs=[sessions_state, session_id_state],
            outputs=[session_radio],
        )

        msg_box.submit(
            on_send_message,
            inputs=[token_state, session_id_state, msg_box, chatbot],
            outputs=[chatbot, msg_box, session_id_state, sessions_state],
        ).then(
            lambda s, sid: gr.update(choices=_session_choices(s), value=sid),
            inputs=[sessions_state, session_id_state],
            outputs=[session_radio],
        )

    return my_app

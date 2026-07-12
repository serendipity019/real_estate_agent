"""
ui/gradio_app.py — Gradio Blocks UI for the Smart Real Estate Assistant.

Layout(logged-in):
  - 💬 Chat tab:  sidebar (session list, new/rename/delete) + chat panel
  - 🛠️ Admin tab: shown only to superusers — KB stats, single ingest,
    batch ingest from .txt file upload, reset

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

def _format_kb_stats(stats: dict) -> str:
    total = stats.get("total_documents", 0)
    categories = stats.get("categories", {})
    sources = stats.get("sources", [])

    cat_lines = "\n".join(
        f"  • **{cat}**: {count} chunks"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])
    ) or "  _(empty)_"

    src_lines = "\n".join(
        f"  • {src}" for src in sorted(sources)
    ) or "  _(no sources)_"

    return (
        f"### 📊 Knowledge Base Statistics\n\n"
        f"**Total chunks:** {total}\n\n"
        f"**By category:**\n{cat_lines}\n\n"
        f"**Sources ({len(sources)}):**\n{src_lines}"
    )

#----------------Auth callbacks---------------------------
def do_login(email: str, password: str)-> list:
    if not email or not password:
        return(
            gr.update(value="Please enter both email and password.", visible=True),
            None, None, gr.update(visible=True), gr.update(visible=False),
            [], None, [], "", gr.update(visible=False), gr.update(choices=[]),
            "_Not authenticated._"
        )
    try:
        token = api.login(email, password)
        user = api.get_current_user(token)
        sessions = api.list_sessions(token)
    except api.APIError as e:
        return(
            gr.update(value=f"Login failed: {e.detail}", visible=True),
            None, None, gr.update(visible=True), gr.update(visible=False),
            [], None, [], "", gr.update(visible=False), gr.update(choices=[]),
            "_Not authenticated._"
        )
    
    is_admin = user.get("is_superuser", False)
    welcome = f"Logged in as **{user['email']}**" + (" 🔑 _(admin)_" if is_admin else "")
    return(
        gr.update(value="", visible=False),
        token, user,
        gr.update(visible=False), gr.update(visible=True),
        sessions, None, [], welcome, gr.update(visible=is_admin), 
        gr.update(choices=_session_choices(sessions)),
        _format_kb_stats(api.get_kb_stats(token)) if is_admin else "_Not authenticaed._",
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

def on_send_message(token: str, session_id: str, message: str, chat_history: list):
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

# ---- Admin callbacks -------------
def admin_load_stats(token: str):
    """Called when the admin tab becomes visible -refresh Knowledge Base stats"""
    if not token:
        return "⚠️ Not authenticated."
    try: 
        stats = api.get_kb_stats(token)
        return _format_kb_stats(stats)
    except api.APIError as e:
        return f"⚠️ Error loading stats: {e.detail}"
    
def on_admin_tab_selected(token: str):
    """Called when admin tab is selected."""
    if not token:
        return "⚠️ Not authenticated."
    try:
        stats = api.get_kb_stats(token)
        return _format_kb_stats(stats)
    except api.APIError as e:
        return f"⚠️ Error loading stats: {e.detail}."

def admin_ingest_single(token: str, content: str, source: str, category: str):
    """Ingest a single document typed into the text area."""
    if not token:
        return "⚠️ Not authenticated.", ""
    if not content.strip():
        return "⚠️ Content cannot be empty.", ""
    if not source.strip():
        return "⚠️ Source name cannot be empty.", ""
    try:
        result = api.ingest_document(token, content.strip(), source.strip(), category.strip())
        stats = api.get_kb_stats(token)
        return(
            f"✅ {result['message']}",
            _format_kb_stats(stats),
        )
    except api.APIError as e:
        return f"⚠️ Ingest failed: {e.detail}", ""
    
def admin_ingest_files(token: str, files):
    """
       Batch ingest .txt / .pdf files uploaded via the Gradio File component.
       Each file becomes one document; source = filename, category = general.
    """
    if not token:
        return "⚠️ Not authenticated.", ""
    if not files:
        return "⚠️ No files selected.", ""
    docs = []
    skipped = []
    for file_path in files:
        try:
            import pathlib
            p = pathlib.Path(file_path)
            text = p.read_text(encoding="utf-8")
            if not text.strip():
                skipped.append(p.name)
                continue
            docs.append({
                "content": text,
                "source": p.name,
                "category": "general",
                "metadata": {"origin": "admin_upload"},
            })
        except Exception as ex:
            skipped.append(f"{file_path} ({ex})")
    if not docs:
        return "⚠️  All files were empty or unreadable.", ""
    
    try:
        result = api.ingest_batch(token, docs)
        stats = api.get_kb_stats(token)
        msg = f"✅  {result['message']}"
        if skipped:
            msg += f"\n⚠️ Skipped: {', '.join(skipped)}"
        return msg, _format_kb_stats(stats)
    except api.APIError as e:
        return f"⚠️ Batch ingest failed: {e.detail}", ""
    
def admin_reset_kb(token: str, confirm_text: str):
        """
        Wipe out and recreate the knowledge base.
        Required from the user to type RESET in the confirmation box."""
        if not token:
            return "⚠️ Not authenticated.", "" 
        if confirm_text.strip().upper() != "RESET":    
            return "⚠️ Type RESET in the confirmation box to proceed.", ""
        try:
            api.reset_knowledge_base(token)
            stats = api.get_kb_stats(token)
            return "✅ Knowledge base wiped out and reset successfully.", _format_kb_stats(stats)
        except api.APIError as e:
            return f"⚠️ Reset failed: {e.detail}", ""
    

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

            
            with gr.Tabs(selected=0) as main_tabs:

            # --- Tab 1: Chat --------------
                with gr.Tab("💬 chat"):    
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
                                placeholder="Ask about Athens property prices, "
                                 "objective zone values or mortgage calculations…",
                            )
                            send_btn = gr.Button("Send", variant="primary")
            
            # --- Tab 2: Admin Dashboard (Admin only) --------------
                with gr.Tab("🛠 Admin", visible= False) as admin_tab:
                    gr.Markdown(
                        "## Knowledge Base Management\n"
                        "All changes take effect immediately for all users."
                    )

                    # Stats panel (This is always visible at top of admin tab)
                    kb_stats_md = gr.Markdown("_Loading..._")

                    gr.Markdown("---")

                    # --- Section A: Single document ingest ------
                    with gr.Accordion("📄 Ingest single document", open=True):
                        ingest_content = gr.Textbox(
                            label="Document content",
                            placeholder=(
                                "Paste the full text of the market report,"
                                "legal document, or neighbourhood data here..."
                            ),
                            lines=8,
                        )
                        with gr.Row():
                            ingest_source = gr.Textbox(
                                label="Source name",
                                placeholder="e.g spitogatos_q3_2025.txt",
                                scale=2,
                            )
                            ingest_category = gr.Dropdown(
                                choices=["general", "market_data", "neighborhood", "legal"],
                                value="Market_data",
                                label="Category",
                                scale=1,
                            )
                        ingest_single_btn = gr.Button("Ingest document", variant="primary") 
                        ingest_single_msg = gr.Markdown()
                    
                    # --- Section B: Batch ingest from .txt or .pdf files ------
                    with gr.Accordion("📁 Batch ingest from .txt/.pdf files", open=False):
                        gr.Markdown(
                            "Upload one or more `.txt` or `.pdf` files. Each file becomes one document."
                            "The filename is used as the source name, category defaults to `general` "
                            "(you can re-ingest with a different category later if needed)."
                        )
                        file_upload = gr.File(
                            label="Upload files",
                            file_types=[".txt", ".pdf"],
                            file_count="multiple",
                        )
                        ingest_files_btn = gr.Button("Ingest files", variant="primary")
                        ingest_files_msg = gr.Markdown()
                    
                    # ---- Section C: Reset -----------
                    with gr.Accordion("🗑 Reset knowledge base", open=False):
                        gr.Markdown(
                            "⚠️ **This permanently deletes all documents** from the vector store. "
                            "Type **RESET** in the box below to confirm."
                        )
                        reset_confirm = gr.Textbox(
                            label="Type RESET to confirm",
                            placeholder="RESET",
                        )
                        reset_btn = gr.Button("🗑 Wipe out knowledge base", variant="stop")
                        reset_msg = gr.Markdown()

        # ---- Wiring: Auth ----------------------------------------------------------
        login_btn.click(
            do_login,
            inputs=[login_email, login_password],
            outputs=[
                login_error, token_state, user_state,
                logged_out_view, logged_in_view,
                sessions_state, session_id_state, chatbot,
                welcome_text, admin_tab, session_radio, kb_stats_md,
            ],
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

        # ---- Wiring: Admin - Single ingest ------
        ingest_single_btn.click(
            admin_ingest_single,
            inputs=[token_state, ingest_content, ingest_source, ingest_category],
            outputs=[ingest_single_msg, kb_stats_md]
        ).then(
            # Clear the text area after successful ingest
            lambda msg: gr.update(value="") if msg.startswith("✅") else gr.update(),
            inputs=[ingest_single_msg],
            outputs=[ingest_content],
        )

        # ----- Wiring: Admin - File ingest ---------
        admin_tab.select(
            on_admin_tab_selected,
            inputs=[token_state],
            outputs=[kb_stats_md]
        )

        ingest_files_btn.click(
            admin_ingest_files,
            inputs=[token_state, file_upload],
            outputs=[ingest_files_msg, kb_stats_md],
        )

        # ------ Wiring: Admin - Reset KB ---------
        reset_btn.click(
            admin_reset_kb,
            inputs=[token_state, reset_confirm],
            outputs=[reset_msg, kb_stats_md],
        ).then(
            lambda msg: gr.update(value="") if msg.startswith("✅") else gr.update(),
            inputs=[reset_msg],
            outputs=[reset_confirm],
        )

    return my_app

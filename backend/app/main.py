"""
app/main.py — FastAPI application factory.
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.config import settings
from app.core import db as db_module
from app.api import api_router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🏠 Starting %s (env=%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Initialize database (creates tables and superuser)
    try:
        with Session(db_module.engine) as session:
            db_module.init_db(session)
        logger.info("✅ Database initialised, tables and superuser ensured.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # In production, you might want to raise this
        if settings.ENVIRONMENT == "production":
            raise
        # In development, continue anyway (might be a migration issue)
        logger.warning("⚠️  Continuing despite database initialization error...")

    # Warm up the RAG pipeline on startup so the first request isn't slow
    try:
        from app.rag.pipeline import get_pipeline
        pipeline = get_pipeline()
        doc_count = pipeline.count()
        logger.info("✅ RAG pipeline ready — %d documents in store.", doc_count)
    except Exception as e:
        logger.warning(f"⚠️  RAG pipeline warm-up failed: {e}")
        logger.warning("   RAG features may not work until pipeline is initialized.")

    # Pre-compile the LangGraph so the first chat request isn't slow
    try:
        from app.agent.graph import build_graph
        build_graph()
        logger.info("✅ LangGraph agent compiled and ready.")
    except Exception as e:
        logger.warning(f"⚠️  LangGraph compilation failed: {e}")
        logger.warning("   Chat features may experience a delay on first use.")

    yield  # app is running

    logger.info("👋 Shutting down %s.", settings.PROJECT_NAME)


# ── App factory ────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Generative AI assistant for the Greek real estate market. "
            "Combines RAG-powered market insights with mortgage calculations, "
            "behind authenticated, session-based chat."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins if settings.all_cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    # Mount the Gradio chat UI at /ui — talks to this same FastAPI app over HTTP
    try:
        import gradio as gr
        from app.ui.gradio_app import build_gradio_app

        my_app = build_gradio_app()
        gr.mount_gradio_app(app, my_app, path="/ui")
        logger.info("✅ Gradio UI mounted at /ui")

    # Don't crash the app if UI fails, but log the error
    except Exception as e:
        logger.error(f"❌ Failed to mount Gradio UI: {e}")

    return app


app = create_app()

# ── For running directly ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
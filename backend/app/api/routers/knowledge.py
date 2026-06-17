"""
routers/knowledge.py — Endpoints for managing the RAG knowledge base.

POST /knowledge/ingest          — add one document
POST /knowledge/ingest/batch    — add many documents at once
GET  /knowledge/stats           — collection statistics
DELETE /knowledge/reset         — wipe the collection (dev/test only)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.api.depedencies import required_active_superuser
from app.schemas.rag_schemas import (
    DocumentIn,
    IngestResponse,
    CollectionStatsResponse,
)
from app.rag.pipeline import RAGPipeline, get_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ── Single document ingest ──────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(required_active_superuser)])
def ingest_document(
    doc: DocumentIn,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    """
    Chunk, embed, and store a single document in the vector database.

    The document will be split into overlapping ~200-character chunks
    before embedding, so long PDFs / market reports work fine.
    """
    try:
        added = pipeline.ingest_document(
            content=doc.content,
            source=doc.source,
            category=doc.category,
            metadata=doc.metadata,
        )
        return IngestResponse(
            success=True,
            documents_added=added,
            collection_size=pipeline.count(),
            message=f"Successfully ingested '{doc.source}' as {added} chunk(s).",
        )
    except Exception as exc:
        logger.exception("Ingest failed for source '%s'", doc.source)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Batch ingest ────────────────────────────────────────────────────────────────

@router.post("/ingest/batch", response_model=IngestResponse, tags=["Ingest"], 
             dependencies=[Depends(required_active_superuser)]) # Admin only
def ingest_batch(
    docs: list[DocumentIn],
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> IngestResponse:
    """Ingest multiple documents in one request."""
    if not docs:
        raise HTTPException(status_code=400, detail="No documents provided.")
    try:
        doc_dicts = [d.model_dump() for d in docs]
        added = pipeline.ingest_batch(doc_dicts)
        return IngestResponse(
            success=True,
            documents_added=added,
            collection_size=pipeline.count(),
            message=f"Batch ingest complete: {added} chunk(s) from {len(docs)} document(s).",
        )
    except Exception as exc:
        logger.exception("Batch ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Stats ────────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=CollectionStatsResponse, tags=["Stats"], 
            dependencies=[Depends(required_active_superuser)]) # Admin only
def collection_stats(
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> CollectionStatsResponse:
    """Return the current state of the knowledge base."""
    stats = pipeline.get_stats()
    return CollectionStatsResponse(
        collection_name="greek_real_estate",
        **stats,
    )


# ── Reset (dev only) ─────────────────────────────────────────────────────────────

@router.delete("/reset", summary="⚠️ Wipe all documents from the knowledge base", tags=["Reset"], 
               dependencies=[Depends(required_active_superuser)]) # Admin only
def reset_collection(
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> dict:
    """Delete and recreate the ChromaDB collection. Use with caution."""
    pipeline.reset()
    return {"success": True, "message": "Knowledge base wiped and reset."}

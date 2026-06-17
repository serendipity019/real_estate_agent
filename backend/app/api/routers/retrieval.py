"""
routers/retrieval.py — Endpoints for querying the knowledge base. Admin-only

POST /retrieval/query   — semantic search, returns ranked chunks
POST /retrieval/context — same search but returns a formatted LLM-ready context string
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.api.depedencies import required_active_superuser
from app.schemas.rag_schemas import QueryRequest, QueryResponse, RetrievedChunk
from app.rag.pipeline import RAGPipeline, get_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


@router.post("/query", response_model=QueryResponse, tags=["Query"],  # Admin only
            dependencies=[Depends(required_active_superuser)] )
def semantic_query(
    req: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> QueryResponse:
    """
    Embed the query and return the most relevant document chunks.

    Useful for inspecting what the RAG system would feed to the LLM.
    """
    if pipeline.count() == 0:
        return QueryResponse(query=req.query, chunks=[], total_found=0)

    try:
        raw_chunks = pipeline.retrieve(
            query=req.query,
            top_k=req.top_k,
            category_filter=req.category_filter,
        )
        chunks = [RetrievedChunk(**c) for c in raw_chunks]
        return QueryResponse(query=req.query, chunks=chunks, total_found=len(chunks))
    except Exception as exc:
        logger.exception("Retrieval failed for query: %s", req.query)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/context", tags=["Context"], 
            dependencies=[Depends(required_active_superuser)] ) # Admin only
def build_context(
    req: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> dict:
    """
    Return the formatted context string that would be injected into an LLM prompt.

    Handy for debugging prompt construction.
    """
    if pipeline.count() == 0:
        return {
            "query": req.query,
            "context": "Knowledge base is empty. Please ingest documents first.",
            "chunks_used": 0,
        }

    try:
        chunks = pipeline.retrieve(
            query=req.query,
            top_k=req.top_k,
            category_filter=req.category_filter,
        )
        context = pipeline.build_context(chunks)
        return {
            "query": req.query,
            "context": context,
            "chunks_used": len(chunks),
        }
    except Exception as exc:
        logger.exception("Context build failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

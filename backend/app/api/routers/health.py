"""
routers/health.py — Liveness and readiness endpoints.
"""
from fastapi import APIRouter, Depends

from api.depedencies import required_active_superuser
from app.schemas.rag_schemas import HealthResponse
from app.rag.pipeline import RAGPipeline, get_pipeline
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, dependencies=[Depends(required_active_superuser)])
def health_check(pipeline: RAGPipeline = Depends(get_pipeline)) -> HealthResponse:
    """Returns service status and basic knowledge-base metrics. Admin only""" 
    return HealthResponse(
        status="ok",
        collection_name=settings.CHROMA_COLLECTION_NAME,
        documents_in_store=pipeline.count(),
        embedding_model=settings.EMBEDDING_MODEL,
    )


@router.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "Smart Real Estate Assistant API — visit /docs for the Swagger UI."}

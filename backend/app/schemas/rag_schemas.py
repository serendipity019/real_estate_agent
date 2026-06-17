from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

"""
Pydantic request/response schemas for the RAG knowledge base endpoints.
"""

# Ingest 

class DocumentIn(BaseModel):
    """A single document to be ingested into the knowledge base."""
    content: str = Field(..., description="Raw text content of the document")
    source: str = Field(..., description="Source identifier, e.g. 'athens_market_2024.pdf'")
    category: str = Field(
        default="general",
        description="Category tag: 'market_data' | 'neighborhood' | 'legal' | 'general'"
    )
    metadata: dict = Field(default_factory=dict, description="Any extra metadata")


class IngestResponse(BaseModel):
    """Result of a document ingestion operation with summary metrics."""
    success: bool
    documents_added: int
    collection_size: int
    message: str


#  Query / Retrieval

class QueryRequest(BaseModel):
    """Search query request with optional top-k and category filtering."""
    query: str = Field(..., min_length=3, description="Natural-language query")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Override default top-k")
    category_filter: Optional[str] = Field(None, description="Filter results by category")


class RetrievedChunk(BaseModel):
    """A retrieved document chunk with source metadata and relevance score."""
    content: str
    source: str
    category: str
    score: float
    metadata: dict = {}


class QueryResponse(BaseModel):
    """Retrieved chunks and total matches for a query."""
    query: str
    chunks: list[RetrievedChunk]
    total_found: int


# Health 

class HealthResponse(BaseModel):
    """Health endpoint response containing operational status and metadata."""
    status: str
    collection_name: str
    documents_in_store: int
    embedding_model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Collection Management 

class CollectionStatsResponse(BaseModel):
    """Aggregated statistics for a collection, including categories and sources."""
    collection_name: str
    total_documents: int
    categories: dict[str, int]
    sources: list[str]
"""
rag/pipeline.py — High-level RAG operations used by routers.

Splits long documents into overlapping chunks before embedding,
then delegates storage to VectorStore.
"""
import re
import logging
from functools import lru_cache

from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ── Chunking constants ──────────────────────────────────────────────────────────
CHUNK_SIZE = 200        # characters per chunk
CHUNK_OVERLAP = 40     # overlap between consecutive chunks


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping fixed-size chunks.
    Respects sentence boundaries where possible.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at a sentence boundary
        if end < len(text):
            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("! ", start, end),
                text.rfind("? ", start, end),
                text.rfind("\n", start, end),
            )
            if boundary > start:
                end = boundary + 1

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]


class RAGPipeline:
    """Thin orchestration layer between API routers and VectorStore."""

    def __init__(self, vector_store: VectorStore) -> None:
        self._store = vector_store

    # ── Ingest ──────────────────────────────────────────────────────────────────

    def ingest_document(
        self,
        content: str,
        source: str,
        category: str = "general",
        metadata: dict | None = None,
    ) -> int:
        """Chunk a document and add all chunks to the vector store."""
        chunks = _chunk_text(content)
        logger.info("Ingesting '%s' → %d chunk(s)", source, len(chunks))

        sources = [source] * len(chunks)
        categories = [category] * len(chunks)
        metadatas = [{**(metadata or {}), "chunk_index": i} for i in range(len(chunks))]

        return self._store.add_documents(chunks, sources, categories, metadatas)

    def ingest_batch(self, documents: list[dict]) -> int:
        """
        Ingest a list of document dicts. Each dict must have:
          - content  (str)
          - source   (str)
          - category (str, optional)
          - metadata (dict, optional)
        """
        total = 0
        for doc in documents:
            total += self.ingest_document(
                content=doc["content"],
                source=doc["source"],
                category=doc.get("category", "general"),
                metadata=doc.get("metadata"),
            )
        return total

    # ── Retrieve ─────────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        category_filter: str | None = None,
    ) -> list[dict]:
        """Semantic retrieval — returns ranked chunks."""
        return self._store.query(query, top_k=top_k, category_filter=category_filter)

    def build_context(self, chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a single context string
        suitable for injection into an LLM prompt.
        """
        if not chunks:
            return "No relevant information found in the knowledge base."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[Source {i}: {chunk['source']} | {chunk['category']} | score={chunk['score']}]\n"
                f"{chunk['content']}"
            )
        return "\n\n---\n\n".join(parts)

    # ── Delegation helpers ────────────────────────────────────────────────────────

    def count(self) -> int:
        return self._store.count()

    def get_stats(self) -> dict:
        return self._store.get_stats()

    def reset(self) -> None:
        self._store.delete_collection()


# ── Singleton factory ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_pipeline() -> RAGPipeline:
    """Return the app-wide RAGPipeline instance (created once)."""
    store = VectorStore()
    return RAGPipeline(store)

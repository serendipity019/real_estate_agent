"""
rag/vector_store.py — ChromaDB wrapper for the Greek Real Estate knowledge base.

Responsibilities:
  - Initialise / persist the ChromaDB collection
  - Add documents with OpenAI embeddings
  - Semantic similarity search with optional category filtering
  - Collection stats for health/admin endpoints
"""
import uuid
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages the ChromaDB collection and all embedding operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._openai = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Persistent client — survives server restarts
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
        logger.info(
            "VectorStore ready — collection '%s' has %d documents.",
            settings.CHROMA_COLLECTION_NAME,
            self._collection.count(),
        )

    # ── Embedding ───────────────────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using OpenAI's embedding model."""
        response = self._openai.embeddings.create(
            model=self._settings.EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    # ── Ingest ──────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        contents: list[str],
        sources: list[str],
        categories: list[str],
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        Embed and store documents in ChromaDB.

        Returns the number of documents successfully added.
        """
        if not contents:
            return 0

        if metadatas is None:
            metadatas = [{} for _ in contents]

        # Merge category & source into each metadata dict so we can filter later
        enriched_meta = [
            {**m, "source": src, "category": cat}
            for m, src, cat in zip(metadatas, sources, categories)
        ]

        embeddings = self._embed(contents)
        ids = [str(uuid.uuid4()) for _ in contents]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=enriched_meta,
        )

        logger.info("Added %d documents. Collection size: %d", len(contents), self._collection.count())
        return len(contents)

    # ── Query ───────────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
        category_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic search against the collection.

        Returns a list of dicts with keys:
          content, source, category, score, metadata
        """
        k = top_k or self._settings.RAG_TOP_K

        where_clause = {"category": {"$eq": category_filter}} if category_filter else None

        query_embedding = self._embed([query_text])[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, max(self._collection.count(), 1)),
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance → similarity score (1 = identical)
            score = 1 - distance
            if score < self._settings.RAG_SIMILARITY_THRESHOLD:
                continue

            chunks.append(
                {
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "category": meta.get("category", "general"),
                    "score": round(score, 4),
                    "metadata": {k: v for k, v in meta.items() if k not in ("source", "category")},
                }
            )

        logger.info("Query returned %d chunks above threshold.", len(chunks))
        return chunks

    # ── Stats ───────────────────────────────────────────────────────────────────

    def count(self) -> int:
        return self._collection.count()

    def get_stats(self) -> dict:
        """Return category breakdown and unique sources."""
        if self._collection.count() == 0:
            return {"total_documents": 0, "categories": {}, "sources": []}

        all_items = self._collection.get(include=["metadatas"])
        categories: dict[str, int] = {}
        sources: set[str] = set()

        for meta in all_items["metadatas"]:
            cat = meta.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
            src = meta.get("source", "unknown")
            sources.add(src)

        return {
            "total_documents": self._collection.count(),
            "categories": categories,
            "sources": sorted(sources),
        }

    def delete_collection(self) -> None:
        """Wipe all documents — useful for testing / resets."""
        self._client.delete_collection(self._settings.CHROMA_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self._settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.warning("Collection '%s' wiped and recreated.", self._settings.CHROMA_COLLECTION_NAME)

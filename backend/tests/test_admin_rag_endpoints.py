"""
tests/test_admin_rag_endpoints.py — Verify /health, /knowledge/*, /retrieval/*
are properly gated behind required_active_superuser.
"""
from unittest.mock import MagicMock, patch


def _mock_pipeline():
    p = MagicMock()
    p.count.return_value = 0
    p.get_stats.return_value = {"total_documents": 0, "categories": {}, "sources": []}
    p.ingest_document.return_value = 1
    p.ingest_batch.return_value = 2
    p.retrieve.return_value = []
    p.build_context.return_value = "No relevant information found in the knowledge base."
    return p


def test_health_requires_superuser(client, normal_user_token_headers):
    resp = client.get("/health", headers=normal_user_token_headers)
    assert resp.status_code == 403


def test_health_accessible_to_superuser(client, superuser_token_headers):
    from app.rag.pipeline import get_pipeline

    pipeline = _mock_pipeline()
    client.app.dependency_overrides[get_pipeline] = lambda: pipeline
    try:
        resp = client.get("/health", headers=superuser_token_headers)
    finally:
        client.app.dependency_overrides.pop(get_pipeline, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_requires_auth_at_all(client):
    resp = client.get("/health")
    assert resp.status_code == 401


def test_knowledge_ingest_requires_superuser(client, normal_user_token_headers):
    resp = client.post(
        "/knowledge/ingest",
        json={"content": "test", "source": "test.txt"},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 403


def test_knowledge_ingest_works_for_superuser(client, superuser_token_headers):
    from app.rag.pipeline import get_pipeline

    pipeline = _mock_pipeline()
    client.app.dependency_overrides[get_pipeline] = lambda: pipeline
    try:
        resp = client.post(
            "/knowledge/ingest",
            json={"content": "Kolonaki prices are high.", "source": "report.txt"},
            headers=superuser_token_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_pipeline, None)

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_knowledge_stats_requires_superuser(client, normal_user_token_headers):
    resp = client.get("/knowledge/stats", headers=normal_user_token_headers)
    assert resp.status_code == 403


def test_knowledge_reset_requires_superuser(client, normal_user_token_headers):
    resp = client.delete("/knowledge/reset", headers=normal_user_token_headers)
    assert resp.status_code == 403


def test_retrieval_query_requires_superuser(client, normal_user_token_headers):
    resp = client.post(
        "/retrieval/query",
        json={"query": "Kolonaki property prices"},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 403


def test_retrieval_query_works_for_superuser(client, superuser_token_headers):
    from app.rag.pipeline import get_pipeline

    pipeline = _mock_pipeline()
    client.app.dependency_overrides[get_pipeline] = lambda: pipeline
    try:
        resp = client.post(
            "/retrieval/query",
            json={"query": "Kolonaki property prices"},
            headers=superuser_token_headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_pipeline, None)

    assert resp.status_code == 200
    assert resp.json()["total_found"] == 0


def test_retrieval_context_requires_superuser(client, normal_user_token_headers):
    resp = client.post(
        "/retrieval/context",
        json={"query": "market trends"},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 403

"""
tests/test_admin_ui.py — Tests for admin dashboard API client methods
and the admin Gradio callback functions.
All HTTP calls are mocked — no running server needed.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.ui import api_client as api
from app.ui import gradio_app as ui


# ── Admin API client tests ────────────────────────────────────────────────────

class TestAdminAPIClient:

    def _mock_get(self, json_data: dict, status: int = 200):
        resp = MagicMock(status_code=status)
        resp.json.return_value = json_data
        return resp

    def _mock_post(self, json_data: dict, status: int = 200):
        resp = MagicMock(status_code=status)
        resp.json.return_value = json_data
        return resp

    def test_get_kb_stats_returns_data(self):
        mock_resp = self._mock_get({
            "collection_name": "greek_real_estate",
            "total_documents": 42,
            "categories": {"market_data": 30, "legal": 12},
            "sources": ["report.txt", "golden_visa.txt"],
        })
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            stats = api.get_kb_stats("token123")
        assert stats["total_documents"] == 42
        assert stats["categories"]["market_data"] == 30

    def test_ingest_document_sends_correct_payload(self):
        mock_resp = self._mock_post({
            "success": True, "documents_added": 3,
            "collection_size": 45, "message": "OK"
        })
        with patch("httpx.Client") as MockClient:
            mock_post = MockClient.return_value.__enter__.return_value.post
            mock_post.return_value = mock_resp
            result = api.ingest_document(
                "token123", "Some content", "report.txt", "market_data"
            )
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["content"] == "Some content"
        assert call_json["source"] == "report.txt"
        assert call_json["category"] == "market_data"
        assert result["documents_added"] == 3

    def test_ingest_batch_sends_list(self):
        mock_resp = self._mock_post({
            "success": True, "documents_added": 6,
            "collection_size": 51, "message": "OK"
        })
        docs = [
            {"content": "A", "source": "a.txt", "category": "general", "metadata": {}},
            {"content": "B", "source": "b.txt", "category": "legal", "metadata": {}},
        ]
        with patch("httpx.Client") as MockClient:
            mock_post = MockClient.return_value.__enter__.return_value.post
            mock_post.return_value = mock_resp
            result = api.ingest_batch("token123", docs)
        sent = mock_post.call_args.kwargs["json"]
        assert len(sent) == 2
        assert result["documents_added"] == 6

    def test_reset_knowledge_base_calls_delete(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"success": True, "message": "Wiped"}
        with patch("httpx.Client") as MockClient:
            mock_delete = MockClient.return_value.__enter__.return_value.delete
            mock_delete.return_value = mock_resp
            result = api.reset_knowledge_base("token123")
        mock_delete.assert_called_once()
        assert result["success"] is True

    def test_get_health_returns_status(self):
        mock_resp = self._mock_get({
            "status": "ok", "collection_name": "greek_real_estate",
            "documents_in_store": 42, "embedding_model": "text-embedding-3-small"
        })
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            health = api.get_health("token123")
        assert health["status"] == "ok"
        assert health["documents_in_store"] == 42

    def test_non_2xx_raises_api_error(self):
        mock_resp = MagicMock(status_code=403)
        mock_resp.json.return_value = {"detail": "Not superuser"}
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            with pytest.raises(api.APIError) as exc_info:
                api.get_kb_stats("regular_user_token")
        assert exc_info.value.status_code == 403


# ── Admin callback tests ──────────────────────────────────────────────────────

class TestAdminCallbacks:

    def test_format_kb_stats_renders_correctly(self):
        stats = {
            "total_documents": 10,
            "categories": {"market_data": 8, "legal": 2},
            "sources": ["a.txt", "b.txt"],
        }
        result = ui._format_kb_stats(stats)
        assert "10" in result
        assert "market_data" in result
        assert "a.txt" in result

    def test_format_kb_stats_empty(self):
        stats = {"total_documents": 0, "categories": {}, "sources": []}
        result = ui._format_kb_stats(stats)
        assert "0" in result
        assert "empty" in result.lower()

    def test_admin_load_stats_no_token(self):
        result = ui.admin_load_stats(None)
        assert "Not authenticated" in result or "authenticated" in result.lower()

    def test_admin_load_stats_success(self):
        with patch.object(ui.api, "get_kb_stats", return_value={
            "total_documents": 5,
            "categories": {"market_data": 5},
            "sources": ["test.txt"],
        }):
            result = ui.admin_load_stats("valid_token")
        assert "5" in result
        assert "market_data" in result

    def test_admin_ingest_single_empty_content(self):
        msg, stats = ui.admin_ingest_single("tok", "", "source.txt", "general")
        assert "empty" in msg.lower() or "⚠️" in msg

    def test_admin_ingest_single_empty_source(self):
        msg, stats = ui.admin_ingest_single("tok", "Some content", "", "general")
        assert "⚠️" in msg

    def test_admin_ingest_single_no_token(self):
        msg, stats = ui.admin_ingest_single(None, "content", "source.txt", "general")
        assert "authenticated" in msg.lower()

    def test_admin_ingest_single_success(self):
        with patch.object(ui.api, "ingest_document", return_value={
            "success": True, "documents_added": 2,
            "collection_size": 10, "message": "Successfully ingested"
        }), patch.object(ui.api, "get_kb_stats", return_value={
            "total_documents": 10, "categories": {}, "sources": []
        }):
            msg, stats = ui.admin_ingest_single(
                "tok", "Market data content", "report.txt", "market_data"
            )
        assert "✅" in msg
        assert "Successfully" in msg

    def test_admin_reset_wrong_confirmation(self):
        msg, stats = ui.admin_reset_kb("tok", "yes")
        assert "RESET" in msg
        assert "⚠️" in msg

    def test_admin_reset_no_token(self):
        msg, stats = ui.admin_reset_kb(None, "RESET")
        assert "authenticated" in msg.lower()

    def test_admin_reset_success(self):
        with patch.object(ui.api, "reset_knowledge_base", return_value={
            "success": True, "message": "Wiped"
        }), patch.object(ui.api, "get_kb_stats", return_value={
            "total_documents": 0, "categories": {}, "sources": []
        }):
            msg, stats = ui.admin_reset_kb("tok", "RESET")
        assert "✅" in msg

    def test_admin_ingest_files_no_token(self):
        msg, stats = ui.admin_ingest_files(None, ["file.txt"])
        assert "authenticated" in msg.lower()

    def test_admin_ingest_files_no_files(self):
        msg, stats = ui.admin_ingest_files("tok", None)
        assert "⚠️" in msg

    def test_admin_ingest_files_success(self, tmp_path):
        # Write a real temporary .txt file
        f = tmp_path / "market_report.txt"
        f.write_text("Τιμές ακινήτων Αθήνα 2025: αύξηση 8%.", encoding="utf-8")

        with patch.object(ui.api, "ingest_batch", return_value={
            "success": True, "documents_added": 1,
            "collection_size": 11, "message": "Batch complete"
        }), patch.object(ui.api, "get_kb_stats", return_value={
            "total_documents": 11, "categories": {}, "sources": []
        }):
            msg, stats = ui.admin_ingest_files("tok", [str(f)])

        assert "✅" in msg

    def test_admin_tab_visibility_in_demo(self):
        """The admin tab should be built as not visible by default."""
        demo = ui.build_gradio_app()
        # Find the admin tab component
        admin_tabs = [
            c for c in demo.blocks.values()
            if type(c).__name__ == "Tab"
            and hasattr(c, "label")
            and c.label is not None
            and "Admin" in str(c.label)
        ]
        assert len(admin_tabs) == 1
        assert admin_tabs[0].visible is False

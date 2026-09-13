"""
tests/test_pdf_extractor.py — Tests for app/rag/pdf_extractor.py

Real PDF creation uses the `fpdf2` library (installed inline if needed).
All tests work without any pre-existing PDF files on disk.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.rag.pdf_extractor import (
    extract_text_from_pdf,
    extract_text_from_file,
    PDFExtractionError,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_real_pdf(tmp_path: Path, text: str, filename: str = "test.pdf") -> Path:
    """Create a real, readable PDF file using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "-q",
                               "--break-system-packages"])
        from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    # Write line by line to avoid encoding issues in the test
    for line in text.split("\n"):
        pdf.cell(0, 10, line, ln=True)

    out = tmp_path / filename
    pdf.output(str(out))
    return out


# ── extract_text_from_pdf ─────────────────────────────────────────────────────

def test_extract_text_from_real_pdf(tmp_path):
    """End-to-end: create a real PDF and extract its text."""
    pdf_path = _make_real_pdf(tmp_path, "Property prices in Athens 2025.\nKolonaki: 4000 EUR/sqm.")
    text = extract_text_from_pdf(pdf_path)
    assert "Athens" in text or "Property" in text
    assert len(text) > 10


def test_extract_text_file_not_found():
    with pytest.raises(PDFExtractionError, match="not found"):
        extract_text_from_pdf("/nonexistent/path/file.pdf")


def test_extract_text_image_only_pdf_raises(tmp_path):
    """
    A PDF with no text layer (image-only) should raise PDFExtractionError.
    We simulate this by mocking pdfplumber to return empty pages.
    """
    fake_page = MagicMock()
    fake_page.extract_text.return_value = ""
    fake_page.extract_tables.return_value = []

    fake_pdf = MagicMock()
    fake_pdf.pages = [fake_page]
    fake_pdf.metadata = {}
    fake_pdf.__enter__ = MagicMock(return_value=fake_pdf)
    fake_pdf.__exit__ = MagicMock(return_value=False)

    pdf_path = tmp_path / "image_only.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")  # file must exist

    with patch("pdfplumber.open", return_value=fake_pdf):
        with pytest.raises(PDFExtractionError, match="no extractable text"):
            extract_text_from_pdf(pdf_path)


def test_extract_text_multi_page_pdf(tmp_path):
    """Multiple pages should be joined with double newlines."""
    text_p1 = "Page one content about real estate."
    text_p2 = "Page two content about mortgage rates."

    page1 = MagicMock()
    page1.extract_text.return_value = text_p1
    page1.extract_tables.return_value = []

    page2 = MagicMock()
    page2.extract_text.return_value = text_p2
    page2.extract_tables.return_value = []

    fake_pdf = MagicMock()
    fake_pdf.pages = [page1, page2]
    fake_pdf.metadata = {}
    fake_pdf.__enter__ = MagicMock(return_value=fake_pdf)
    fake_pdf.__exit__ = MagicMock(return_value=False)

    pdf_path = tmp_path / "multi.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=fake_pdf):
        result = extract_text_from_pdf(pdf_path)

    assert text_p1 in result
    assert text_p2 in result
    assert "\n\n" in result  # pages separated by double newline


def test_extract_text_with_tables(tmp_path):
    """Tables on a page should be included after regular text."""
    page = MagicMock()
    page.extract_text.return_value = "Market report:"
    page.extract_tables.return_value = [
        [["Area", "Price/sqm"], ["Kolonaki", "4000"], ["Pagrati", "2900"]]
    ]

    fake_pdf = MagicMock()
    fake_pdf.pages = [page]
    fake_pdf.metadata = {}
    fake_pdf.__enter__ = MagicMock(return_value=fake_pdf)
    fake_pdf.__exit__ = MagicMock(return_value=False)

    pdf_path = tmp_path / "with_table.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=fake_pdf):
        result = extract_text_from_pdf(pdf_path)

    assert "Market report" in result
    assert "Kolonaki" in result
    assert "4000" in result


# ── extract_text_from_file (universal entry point) ────────────────────────────

def test_universal_extractor_txt_file(tmp_path):
    f = tmp_path / "report.txt"
    f.write_text("Athens prices 2025.", encoding="utf-8")
    result = extract_text_from_file(f)
    assert "Athens prices" in result


def test_universal_extractor_txt_latin1_fallback(tmp_path):
    """Greek text in Latin-1 encoding should not crash."""
    f = tmp_path / "old.txt"
    # Write with latin-1 encoding (legacy Greek files)
    f.write_bytes("Τιμές ακινήτων".encode("latin-1", errors="replace"))
    # Should not raise even if characters are mangled
    result = extract_text_from_file(f)
    assert isinstance(result, str)


def test_universal_extractor_pdf_file(tmp_path):
    page = MagicMock()
    page.extract_text.return_value = "Golden Visa threshold 800000 EUR."
    page.extract_tables.return_value = []

    fake_pdf = MagicMock()
    fake_pdf.pages = [page]
    fake_pdf.metadata = {}
    fake_pdf.__enter__ = MagicMock(return_value=fake_pdf)
    fake_pdf.__exit__ = MagicMock(return_value=False)

    pdf_path = tmp_path / "legal.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("pdfplumber.open", return_value=fake_pdf):
        result = extract_text_from_file(pdf_path)

    assert "Golden Visa" in result


def test_universal_extractor_unsupported_type(tmp_path):
    f = tmp_path / "spreadsheet.xlsx"
    f.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_file(f)

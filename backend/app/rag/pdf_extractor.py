"""
rag/pdf_extractor.py — Extract plain text from PDF files for ingestion
into the ChromaDB knowledge base.

Uses pdfplumber, which handles:
  - Greek text and special characters correctly
  - Multi-column layouts (extracts left-to-right, top-to-bottom)
  - Tables (extracted as structured text rows)
  - Password-protected PDFs (raises an error with a clear message)

The output is plain text ready to be passed directly to the existing
RAGPipeline.ingest_document() method — no changes to the chunking or
embedding pipeline are needed.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or yields no usable text."""
    pass

def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract all text from a PDF file and return it as a single string.

    Iterates page by page, preserving paragraph structure with newlines.
    Tables on each page are extracted as tab-separated rows and appended
    after the regular page text.

    Args:
        file_path: Path to the .pdf file on disk.

    Returns:
        Extracted text as a single string, ready for chunking.

    Raises:
        PDFExtractionError: If the file cannot be opened, is encrypted,
                            or yields no extractable text.
        ImportError: If pdfplumber is not installed.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required for PDF ingestion. "
            "Install it with: pip install pdfplumber"
        )

    path = Path(file_path)
    if not path.exists():
        raise PDFExtractionError(f"File not found: {file_path}")

    logger.info("Extracting text from PDF: %s", path.name)

    try:
        with pdfplumber.open(str(path)) as pdf:
            if pdf.metadata.get("Encrypted"):
                raise PDFExtractionError(
                    f"PDF '{path.name}' is password-protected and cannot be read."
                )
            pages_text: list[str] = []

            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract regular text
                text = page.extract_text(x_tolerance =3, y_tolerance=3) or ""

                # Extract tables and convert to readable text rows
                tables = page.extract_tables()
                table_texts: list[str] = []
                for table in tables:
                    for row in table:
                        # Filter out None cells, join with tab
                        clean_row = "\t".join(
                            cell.strip() if cell else ""
                            for cell in row
                        )
                        if clean_row.strip():
                            table_texts.append(clean_row)

                page_content = text
                if table_texts:
                    page_content = (text + "\n" + "\n".join(table_texts)).strip()

                if page_content:
                    pages_text.append(page_content)
                    logger.debug(
                        "Page %d: extracted %d characters", page_num, len(page_content)
                    )
                else:
                    logger.warning("Page %d: no text extracted (may be image-only)", page_num)

    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(
            f"Failed to read PDF '{path.name}': {exc}"
        ) from exc

    if not pages_text:
        raise PDFExtractionError(
            f"PDF '{path.name}' yielded no extractable text. "
            "It may be a scanned image PDF — consider running OCR first."
        )

    full_text = "\n\n".join(pages_text)
    logger.info(
        "PDF extraction complete: %s — %d pages, %d characters",
        path.name, len(pages_text), len(full_text)
    )
    return full_text

def extract_text_from_file(file_path: str | Path) -> str:
    """
    Universal text extractor — handles both .txt and .pdf files.
    This is the single entry point used by the ingest pipeline.

    Args:
        file_path: Path to a .txt or .pdf file.

    Returns:
        Extracted text as a string.

    Raises:
        PDFExtractionError: For unreadable/encrypted PDFs.
        ValueError: For unsupported file types.
        UnicodeDecodeError: For .txt files with unexpected encoding.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix == ".txt":
        # Try UTF-8 first, fall back to latin-1 for legacy Greek encodings
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "%s: UTF-8 decode failed, retrying with latin-1", path.name
            )
            return path.read_text(encoding="latin-1")
        else:
            raise ValueError(
                f"Unsupported file type '{suffix}'. Supported: .txt, .pdf"
            )

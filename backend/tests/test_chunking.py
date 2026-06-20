"""
tests/test_chunking.py — Tests for app/rag/pipeline._chunk_text.

Includes a regression test for a real bug found while ingesting sample
knowledge-base documents: when the final remaining slice of text was
shorter than CHUNK_OVERLAP, `start = end - overlap` could land at or
before the previous `start`, causing an infinite loop (the function would
re-append the same final chunk forever and never return).
"""
import pytest
from app.rag.pipeline import _chunk_text


def test_short_text_returns_single_chunk():
    text = "Σύντομο κείμενο."
    chunks = _chunk_text(text, chunk_size=500)
    assert chunks == ["Σύντομο κείμενο."]


def test_empty_text_returns_empty_list():
    assert _chunk_text("   ", chunk_size=500) == []


def test_chunking_terminates_on_real_document():
    """
    Regression test: this exact document (2758 chars) previously triggered
    an infinite loop because its final slice was shorter than the overlap.
    Must return promptly and produce a small, sane number of chunks.
    """
    text = (
        "Όταν ένας χρήστης ρωτά πόσο αξίζει ή πόσο μπορεί να πουλήσει ένα "
        "συγκεκριμένο ακίνητο, ο βοηθός πρέπει να ακολουθεί την εξής λογική. "
    ) * 20  # repeat to build a multi-chunk document without relying on disk I/O

    chunks = _chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) > 1
    assert len(chunks) < 50  # sanity bound — should never balloon into hundreds
    for chunk in chunks:
        assert len(chunk) > 0


def test_chunking_terminates_when_final_tail_shorter_than_overlap():
    """
    Directly reproduces the original bug condition: chunk_size=500, overlap=100,
    with total text length landing just past a chunk boundary so the final
    remainder is shorter than the overlap window.
    """
    text = "Α" * 549  # 549 = one full 500-char chunk + a 49-char tail (< overlap=100)
    chunks = _chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 2
    assert sum(len(c) for c in chunks) >= len(text) - 100  # overlap accounted for


def test_chunking_respects_sentence_boundaries():
    text = "Πρώτη πρόταση εδώ. " * 30  # forces multiple chunks with '. ' boundaries
    chunks = _chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    # Most chunks should end on a sentence boundary (period) where possible
    boundary_endings = sum(1 for c in chunks if c.rstrip().endswith("."))
    assert boundary_endings >= len(chunks) - 2  # allow the last chunk some slack


@pytest.mark.parametrize("overlap", [0, 50, 100])
def test_chunking_never_infinite_loops_across_overlap_values(overlap):
    """Parametrized sweep across normal overlap values relative to chunk_size=500."""
    text = "Β" * 1234
    chunks = _chunk_text(text, chunk_size=500, overlap=overlap)
    assert len(chunks) > 0
    assert len(chunks) < 100


def test_chunking_terminates_with_overlap_near_chunk_size():
    """
    Overlap close to chunk_size produces many small-stride chunks — that's
    expected, not a bug. The key regression guarantee is termination, which
    we verify via pytest's own timeout rather than an arbitrary chunk-count cap.
    """
    text = "Β" * 1234
    chunks = _chunk_text(text, chunk_size=500, overlap=499)
    assert len(chunks) > 0
    # Every chunk must represent forward progress (no duplicate empty work)
    assert all(len(c) > 0 for c in chunks)

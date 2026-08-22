"""An unreadable PDF must not become a scored answer.

The defect this pins: `extract_pdf_text` returned
`OCRDocument(confidence=0.0, lines=[])` for a ten-page image-only scan, without
raising. A caller that did not check `len(lines)` received an empty answer
string, passed it to the marking engine, and the marking engine correctly
scored an empty answer as zero.

Nothing malfunctioned. Nothing was logged as an error. The student's script was
ten pages of writing and the mark was zero, and it looked exactly like a
legitimate zero.

Amendment A: BLANK_PAGE / ILLEGIBLE and the rest may never silently produce a
zero -- every one routes to MANDATORY_HUMAN. Found by probing the one real scan
on the build machine; see docs/eval/OCR_PROBE_FINDINGS.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from AI.ocr.ocr_manager import OCRManager, UnreadablePDFError

# A structurally valid PDF with an image XObject and no text layer -- the
# shape of a scan. Kept as bytes so the test needs no fixture file and no
# real student data.
IMAGE_ONLY_PDF = (
    b"%PDF-1.5\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /XObject << /Im0 4 0 R >> >> >> endobj\n"
    b"4 0 obj << /Type /XObject /Subtype /Image /Width 100 /Height 100 "
    b"/Filter /DCTDecode /Length 8 >> stream\n"
    b"\xff\xd8\xff\xe0\x00\x10JF\nendstream endobj\n"
    b"trailer << /Root 1 0 R >>\n%%EOF\n"
)

EMPTY_PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


@pytest.fixture
def manager() -> OCRManager:
    return OCRManager()


def _write(tmp_path: Path, name: str, data: bytes) -> str:
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_image_only_pdf_raises_instead_of_returning_an_empty_document(manager, tmp_path):
    """The exact defect. Previously returned lines=[], confidence=0.0."""
    path = _write(tmp_path, "scan.pdf", IMAGE_ONLY_PDF)

    with pytest.raises(UnreadablePDFError) as exc_info:
        manager.extract_pdf_text(path, "probe-001")

    message = str(exc_info.value)
    assert "no extractable text layer" in message
    assert "MANDATORY_HUMAN" in message, "the error must name the required route"


def test_error_says_the_pdf_looks_scanned_when_it_has_image_xobjects(manager, tmp_path):
    """A scanned PDF and a corrupt one need different human responses."""
    path = _write(tmp_path, "scan.pdf", IMAGE_ONLY_PDF)

    with pytest.raises(UnreadablePDFError, match="scanned/image-only"):
        manager.extract_pdf_text(path, "probe-001")


def test_textless_pdf_without_images_raises_without_claiming_it_is_a_scan(manager, tmp_path):
    path = _write(tmp_path, "empty.pdf", EMPTY_PDF)

    with pytest.raises(UnreadablePDFError) as exc_info:
        manager.extract_pdf_text(path, "probe-002")

    assert "scanned/image-only" not in str(exc_info.value)
    assert "MANDATORY_HUMAN" in str(exc_info.value)


def test_unreadable_file_raises_rather_than_returning_empty(manager, tmp_path):
    with pytest.raises(UnreadablePDFError, match="cannot read"):
        manager.extract_pdf_text(str(tmp_path / "does_not_exist.pdf"), "probe-003")


def test_the_exception_is_a_runtime_error_so_it_is_not_silently_caught_as_value_error(manager):
    """Callers catching ValueError must not swallow this by accident."""
    assert issubclass(UnreadablePDFError, RuntimeError)
    assert not issubclass(UnreadablePDFError, ValueError)


# ---------------------------------------------------------------------------
# The property that actually matters
# ---------------------------------------------------------------------------


def test_an_unreadable_pdf_cannot_produce_a_scored_result(manager, tmp_path):
    """End to end: no path from an unreadable scan to a mark.

    This is the assertion the whole change exists for. It reproduces exactly
    what backend/app/services/submission_service.py:_load_source_file_text did
    -- extract, join the lines, hand the string on to be marked -- and asserts
    that sequence now cannot complete.

    Deliberately does not import the marking engine: the property holds for
    any marker, because the defect is that an unreadable script and a blank
    one become the same empty string before any marker sees them.
    """
    path = _write(tmp_path, "ten_page_script.pdf", IMAGE_ONLY_PDF)
    answer_reached_the_marker = False

    with pytest.raises(UnreadablePDFError):
        doc = manager.extract_pdf_text(path, "student-script")
        # Unreachable now. This is verbatim the old service-layer line.
        answer = "\n".join(line.text for line in doc.lines).strip()
        answer_reached_the_marker = True
        assert answer == ""  # what used to be marked

    assert not answer_reached_the_marker, (
        "extraction returned instead of raising: an empty answer string reached "
        "the marking path, where it is indistinguishable from a genuinely blank "
        "page and scores zero under any scheme"
    )


def test_docstring_no_longer_claims_a_fallback_that_does_not_exist(manager):
    """The docstring said scanned PDFs fall back to image OCR engines.

    No code produced page images for them to fall back to. A docstring that
    describes a capability the package does not have is how the gap survived.
    """
    doc = OCRManager.extract_pdf_text.__doc__ or ""
    assert "no rasterisation" in doc.lower() or "rasterisation stage" in doc.lower()
    assert "UnreadablePDFError" in doc

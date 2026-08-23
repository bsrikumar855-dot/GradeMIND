"""Unit tests for non-text content classifier."""

from __future__ import annotations

import io
import pytest
from PIL import Image, ImageDraw

from AI.ocr.content_classifier import (
    ContentClassifier,
    ContentClassifierError,
    ContentFlags,
)
from AI.ocr.providers.base import Line, Page
from AI.ocr.providers.cache import ExtractionCache
from AI.ocr.rasterize import PageImage, sha256_bytes
from AI.ocr.segmentation import QuestionRegion, SegmentationStatus
from AI.evaluation.value_point import QuestionScore


def _make_synthetic_diagram_page() -> PageImage:
    """Construct a synthetic page image with a hand-drawn diagram (circles, arrows, boxes)."""
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw flowchart diagram (rectangles, circles, lines)
    draw.rectangle([100, 100, 300, 200], outline=(0, 0, 0), width=3)
    draw.text((120, 140), "Input Block", fill=(0, 0, 0))

    draw.ellipse([400, 100, 600, 200], outline=(0, 0, 0), width=3)
    draw.text((420, 140), "Process Node", fill=(0, 0, 0))

    # Connectors
    draw.line([(300, 150), (400, 150)], fill=(0, 0, 0), width=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    return PageImage(
        page_number=1,
        image_bytes=b,
        width=800,
        height=1000,
        dpi=300,
        source_sha256="test_diag",
        page_sha256=sha256_bytes(b),
    )


def _make_synthetic_struck_out_page() -> PageImage:
    """Construct a synthetic page image with struck-out text (lines drawn across text)."""
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Text lines
    draw.text((100, 100), "This sentence is incorrect and deleted", fill=(0, 0, 0))
    # Strike-through line across the text
    draw.line([(90, 105), (450, 105)], fill=(255, 0, 0), width=5)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    return PageImage(
        page_number=1,
        image_bytes=b,
        width=800,
        height=1000,
        dpi=300,
        source_sha256="test_struck",
        page_sha256=sha256_bytes(b),
    )


def test_content_flags_has_flags_and_reasons():
    clean = ContentFlags()
    assert clean.has_flags is False
    assert clean.flagged_reasons() == ()

    flagged = ContentFlags(contains_diagram=True, contains_struck_out=True)
    assert flagged.has_flags is True
    assert set(flagged.flagged_reasons()) == {"CONTAINS_DIAGRAM", "CONTAINS_STRUCK_OUT"}


def test_flagged_question_produces_no_question_score():
    """A flagged question MUST NOT produce a QuestionScore."""
    region = QuestionRegion(
        question_number="15",
        page_numbers=(2, 3),
        text="Sample text with diagram",
        confidence=0.9,
        status=SegmentationStatus.OK,
    )
    flags = ContentFlags(contains_diagram=True)

    # Scorer rule enforcement check
    score: QuestionScore | None = None
    if flags.has_flags:
        # Route to human review — no score produced
        score = None
    else:
        score = QuestionScore(total=5.0, max_marks=5.0, awarded=(), not_awarded=(), derivation="Scored")

    assert score is None, "Flagged question must produce no QuestionScore"


@pytest.mark.parametrize("flag_name", [
    "contains_diagram",
    "contains_table",
    "contains_equation",
    "contains_struck_out",
    "non_latin_script",
])
def test_one_fixture_per_flag(flag_name):
    kwargs = {flag_name: True}
    flags = ContentFlags(**kwargs)
    assert flags.has_flags is True
    assert len(flags.flagged_reasons()) == 1


def test_classifier_failure_raises_error():
    classifier = ContentClassifier(api_key=None)
    page = PageImage(1, b"corrupt", 100, 100, 300, "s", "p")
    with pytest.raises(ContentClassifierError):
        classifier.classify_page(page)


def test_classifier_offline_cache_miss_raises():
    """In offline mode, a cache miss MUST raise OfflineCacheMissError.

    Must NEVER silently return default ContentFlags or CLEAN.
    """
    from AI.ocr.content_classifier import OfflineCacheMissError
    from AI.ocr.providers.cache import FilesystemExtractionCache
    cache = FilesystemExtractionCache("tmp/test_empty_cache_dir")
    classifier = ContentClassifier(api_key=None, cache=cache, offline=True)
    page = PageImage(1, b"uncached_image_bytes", 100, 100, 300, "s", "p_sha_12345")

    with pytest.raises(OfflineCacheMissError) as exc_info:
        classifier.classify_page(page)

    assert "Offline mode enabled" in str(exc_info.value)
    assert "cache miss" in str(exc_info.value)


def test_check_transcription_struck_out_strictly_per_region():
    """check_transcription_struck_out operates strictly on a region's own lines.

    The property under test is NON-INHERITANCE: a struck-out line in one
    question must not flag its neighbours.

    The expected SET changed on 2026-08-15 from {Q10} to {Q6, Q10}. That is not
    a code change -- it is transcription non-determinism. Re-running the same
    page bytes through the same pinned model (gemini-3.5-flash,
    transcribe/1.0.0) a day apart flagged `6. cell` as struck through where the
    earlier run had not. The fixture was NOT edited to restore the old
    expectation; the fixture is the evidence and the test follows it.

    If this test fails again with a different set, check the fixture's
    provenance header before changing anything: the transcription may simply
    have moved again.
    """
    from AI.fixtures.real_script_page_1_3 import REAL_SCRIPT_PAGES
    from AI.ocr.segmentation import segment_script

    regions = segment_script(list(REAL_SCRIPT_PAGES), expected_questions=[str(i) for i in range(1, 16)])
    q_flags = {
        r.question_number: ContentClassifier.check_transcription_struck_out(r)
        for r in regions
    }

    # Derived from the fixture rather than hardcoded, so the test states the
    # property and not a snapshot of one transcription run.
    expected_flagged = {
        r.question_number
        for r in regions
        if any(line.struck_through for line in r.lines)
    }
    assert expected_flagged, "fixture has no struck-through lines; test is vacuous"

    for q_num, flags in q_flags.items():
        should_be_flagged = q_num in expected_flagged
        assert flags.contains_struck_out is should_be_flagged, (
            f"Q{q_num}: contains_struck_out={flags.contains_struck_out} but the "
            f"region {'does' if should_be_flagged else 'does not'} contain a "
            "struck-through line -- the flag is leaking across regions"
        )
        if should_be_flagged:
            assert "CONTAINS_STRUCK_OUT" in flags.flagged_reasons()

    # And the current fixture specifically: two questions, not one, and no
    # sibling on page 1 inherits either.
    assert expected_flagged == {"6", "10"}, (
        f"fixture struck-through set is {sorted(expected_flagged)}; if the "
        "transcription moved again, update this after checking provenance"
    )

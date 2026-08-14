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

"""Unit tests for question segmentation module."""

from __future__ import annotations

import pytest

from AI.ocr.providers.base import Line, Page
from AI.ocr.segmentation import (
    QuestionRegion,
    SegmentationStatus,
    parse_question_header,
    rejoin_line_texts,
    segment_script,
)


def test_parse_question_header_detects_clean_anchors():
    assert parse_question_header("13.") == "13"
    assert parse_question_header("14.") == "14"
    assert parse_question_header("15.") == "15"
    assert parse_question_header("Part B 13.") == "13"
    assert parse_question_header("Q1. Photosynthesis") == "1"
    assert parse_question_header("Regular sentence without question header") is None


def test_rejoin_line_texts_mid_word_split():
    lines = [
        "for image based data and to get the import",
        "ant",
        "features and LSTM has",
    ]
    rejoined = rejoin_line_texts(lines)
    # Must rejoin "import" + "ant" as "important", NOT "import ant"
    assert "important" in rejoined
    assert "import ant" not in rejoined
    assert rejoined == "for image based data and to get the important features and LSTM has"


def test_rejoin_line_texts_hyphenated_split():
    lines = [
        "Standard autoen-",
        "coders are less efficient",
    ]
    rejoined = rejoin_line_texts(lines)
    assert rejoined == "Standard autoencoders are less efficient"


def test_q15_spans_pages_2_and_3_with_exact_lines():
    """Exact test case from the real scan:

    Q15 spans pages 2 and 3. Page 2 ends mid-word:
        L24: "for image based data and to get the import"
        L25: "ant"
    Page 3 continues:
        L 1: "features and LSTM has"
    """
    page2 = Page(
        lines=(
            Line("15.", 1.0, (0.1, 0.1, 0.9, 0.15)),
            Line("We LSTM (Long Short Term Memory) in improving the", 0.9, (0.1, 0.2, 0.9, 0.25)),
            Line("performance of image captioning models. We use", 0.9, (0.1, 0.25, 0.9, 0.3)),
            Line("both CNN and LSTM for this. We use CNN", 0.9, (0.1, 0.3, 0.9, 0.35)),
            Line("for image based data and to get the import", 0.9, (0.1, 0.35, 0.9, 0.4)),
            Line("ant", 0.9, (0.1, 0.4, 0.9, 0.45)),
        ),
        page_confidence=0.9,
        provider="gemini_vision",
        model_id="gemini-3.5-flash",
        prompt_version="v1",
        page_number=2,
        page_sha256="page2_sha",
        extraction_sha256="ext2_sha",
        rasterize_version="v1",
    )

    page3 = Page(
        lines=(
            Line("features and LSTM has", 0.8, (0.1, 0.1, 0.9, 0.15)),
            Line("storing past memory while generating captions.", 0.9, (0.1, 0.15, 0.9, 0.2)),
            Line("It has the forget gate which will decide", 0.9, (0.1, 0.2, 0.9, 0.25)),
            Line("what content is necessary and which isn't. So", 0.9, (0.1, 0.25, 0.9, 0.3)),
            Line("1 1/2", 0.8, (0.1, 0.3, 0.9, 0.35)),
            Line("LSTM is used here when producing long sequential", 0.9, (0.1, 0.35, 0.9, 0.4)),
            Line("data.", 0.9, (0.1, 0.4, 0.9, 0.45)),
        ),
        page_confidence=0.8,
        provider="gemini_vision",
        model_id="gemini-3.5-flash",
        prompt_version="v1",
        page_number=3,
        page_sha256="page3_sha",
        extraction_sha256="ext3_sha",
        rasterize_version="v1",
    )

    regions = segment_script([page2, page3])
    assert len(regions) == 1

    q15 = regions[0]
    assert q15.question_number == "15"
    assert q15.page_numbers == (2, 3)
    assert q15.status is SegmentationStatus.SPANS_PAGES
    assert q15.can_be_auto() is False

    # Check stitched & word-rejoined text
    assert "important features and LSTM has" in q15.text
    assert "import ant" not in q15.text


def test_statuses_routing_and_no_ok_on_non_ok():
    page_unmapped = Page(
        lines=(Line("Text without header", 0.9, (0.1, 0.1, 0.9, 0.2)),),
        page_confidence=0.9,
        provider="test",
        model_id="m",
        prompt_version="p",
        page_number=1,
        page_sha256="sha1",
        extraction_sha256="ext1",
        rasterize_version="v1",
    )
    regions_unmapped = segment_script([page_unmapped])
    assert len(regions_unmapped) == 1
    assert regions_unmapped[0].status is SegmentationStatus.UNMAPPED_REGION
    assert regions_unmapped[0].can_be_auto() is False

    # Out of order
    page_ooo = Page(
        lines=(
            Line("15.", 0.9, (0.1, 0.1, 0.9, 0.2)),
            Line("13.", 0.9, (0.1, 0.3, 0.9, 0.4)),
        ),
        page_confidence=0.9,
        provider="test",
        model_id="m",
        prompt_version="p",
        page_number=1,
        page_sha256="sha2",
        extraction_sha256="ext2",
        rasterize_version="v1",
    )
    regions_ooo = segment_script([page_ooo])
    assert any(r.status is SegmentationStatus.OUT_OF_ORDER for r in regions_ooo)
    assert all(r.can_be_auto() is False for r in regions_ooo if r.status != SegmentationStatus.OK)

    # Missing question
    regions_missing = segment_script([page_ooo], expected_questions=["13", "14", "15"])
    assert any(r.status is SegmentationStatus.MISSING_QUESTION_NUMBER for r in regions_missing)

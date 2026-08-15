"""Provider failure paths, cache/replay, and the identity mask.

Gates (d), (e), (f), (g). Every test here injects a transport, so the whole
suite runs with no API key and no network -- which is also the point: the
failure paths are the ones that must be proven, and they are exactly the ones
you cannot exercise against a live, working API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from AI.ocr.identity_mask import IdentityMaskError, MaskRegion, mask_identity_region
from AI.ocr.providers.base import HTRExtractionError, Page
from AI.ocr.providers.cache import (
    CacheMiss,
    FilesystemExtractionCache,
    cache_key,
)
from AI.ocr.providers.gemini_vision import (
    CircuitOpen,
    GeminiVisionHTRProvider,
)
from AI.ocr.providers.prompts import TRANSCRIPTION_PROMPT_VERSION
from AI.ocr.rasterize import PageImage, sha256_bytes


def make_page(
    data: bytes = b"fake-png-bytes", number: int = 1, masked: bool = True
) -> PageImage:
    """Masked by default.

    The provider refuses to transmit a page with identity_masked=False, so the
    default here reflects the only state in which extraction is legitimate.
    Pass masked=False to exercise the refusal.
    """
    return PageImage(
        page_number=number,
        image_bytes=data,
        width=1240,
        height=1755,
        dpi=150,
        source_sha256="source" + "0" * 58,
        page_sha256=sha256_bytes(data),
        identity_masked=masked,
    )


GOOD_RESPONSE = json.dumps(
    {
        "lines": [
            {"text": "Q1. Photosynthesis occurs in the chloroplast.",
             "legibility": 0.91, "bbox": [0.1, 0.2, 0.9, 0.24], "script": "Latin"},
            {"text": "It uses sunlite and carbon dioxide.",
             "legibility": 0.62, "bbox": [0.1, 0.25, 0.9, 0.29], "script": "Latin"},
        ]
    }
)


def transport_returning(payload):
    def _t(image_bytes, prompt):
        return payload
    return _t


def transport_raising(exc):
    def _t(image_bytes, prompt):
        raise exc
    return _t


# ---------------------------------------------------------------------------
# Happy path, so the failure tests mean something
# ---------------------------------------------------------------------------


def test_valid_response_produces_a_page_with_provenance():
    provider = GeminiVisionHTRProvider(
        api_key="test", transport=transport_returning(GOOD_RESPONSE)
    )
    page = provider.extract(make_page())

    assert len(page.lines) == 2
    assert page.lines[0].text.startswith("Q1.")
    assert page.model_id == "gemini-3.5-flash"
    assert page.prompt_version == TRANSCRIPTION_PROMPT_VERSION
    assert page.extraction_sha256
    assert page.provenance()["model_id"] == "gemini-3.5-flash"


def test_page_confidence_is_the_minimum_not_the_mean():
    """One illegible line should pull the page down, not be averaged away."""
    provider = GeminiVisionHTRProvider(
        api_key="test", transport=transport_returning(GOOD_RESPONSE)
    )
    page = provider.extract(make_page())

    assert page.page_confidence == pytest.approx(0.62)


def test_transcription_preserves_the_students_spelling_error():
    """'sunlite' must survive: correcting it would fabricate evidence."""
    provider = GeminiVisionHTRProvider(
        api_key="test", transport=transport_returning(GOOD_RESPONSE)
    )
    page = provider.extract(make_page())

    assert "sunlite" in page.text


def test_model_id_must_not_be_a_floating_alias():
    for alias in ("gemini-flash-latest", "gemini-2.5-flash-exp"):
        with pytest.raises(ValueError, match="floating alias"):
            GeminiVisionHTRProvider(api_key="k", model_id=alias)


# ---------------------------------------------------------------------------
# GATE (d): a malformed response is an error, never a partial Page
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload,reason",
    [
        ("not json at all", "not valid JSON"),
        (json.dumps({"wrong_key": []}), "no 'lines' key"),
        (json.dumps({"lines": "a string"}), "expected list"),
        (json.dumps({"lines": ["a bare string"]}), "expected object"),
        (json.dumps({"lines": [{"legibility": 0.9}]}), "no 'text'"),
        (json.dumps({"lines": [{"text": "x", "legibility": "high"}]}), "not a number"),
        (json.dumps({"lines": [{"text": "x", "legibility": 1.7}]}), "outside"),
        ("", "no text payload"),
    ],
)
def test_malformed_response_raises_and_yields_no_page(payload, reason):
    provider = GeminiVisionHTRProvider(
        api_key="test", transport=transport_returning(payload)
    )
    with pytest.raises(HTRExtractionError, match=reason):
        provider.extract(make_page())


def test_a_partial_page_is_never_returned_from_a_bad_line():
    """One bad line invalidates the whole page, not just that line.

    Dropping the bad line and keeping the rest would silently lose part of a
    student's answer, which is a missing-evidence defect: the mark would be
    computed against an answer the student did not give.
    """
    payload = json.dumps({"lines": [
        {"text": "good line", "legibility": 0.9, "bbox": [0, 0, 1, 0.1]},
        {"text": "bad line", "legibility": 99},
    ]})
    provider = GeminiVisionHTRProvider(api_key="t", transport=transport_returning(payload))

    with pytest.raises(HTRExtractionError):
        provider.extract(make_page())


# ---------------------------------------------------------------------------
# GATE (e): API failure produces no Page at all
# ---------------------------------------------------------------------------


def test_exhausted_retries_raise_rather_than_returning_an_empty_page():
    calls = {"n": 0}

    def counting(image_bytes, prompt):
        calls["n"] += 1
        raise TimeoutError("upstream timeout")

    provider = GeminiVisionHTRProvider(
        api_key="t", transport=counting, max_attempts=3, sleep=lambda s: None
    )

    with pytest.raises(HTRExtractionError, match="MANDATORY_HUMAN"):
        provider.extract(make_page())

    assert calls["n"] == 3, "must exhaust its retries before giving up"


def test_no_scored_result_can_follow_a_failed_extraction():
    """The property the whole failure path exists for.

    Mirrors the sequence a caller would write -- extract, take the text, mark
    it -- and asserts it cannot get past extraction.
    """
    provider = GeminiVisionHTRProvider(
        api_key="t", transport=transport_raising(RuntimeError("503")),
        max_attempts=1, sleep=lambda s: None,
    )
    answer_text = None

    with pytest.raises(HTRExtractionError):
        page = provider.extract(make_page())
        answer_text = page.text  # unreachable

    assert answer_text is None, (
        "extraction returned instead of raising: empty text would reach the "
        "marking path and score zero, indistinguishable from a blank page"
    )


def test_circuit_breaker_opens_and_stops_calling():
    calls = {"n": 0}

    def failing(image_bytes, prompt):
        calls["n"] += 1
        raise RuntimeError("boom")

    provider = GeminiVisionHTRProvider(
        api_key="t", transport=failing, max_attempts=5, sleep=lambda s: None
    )

    with pytest.raises(HTRExtractionError):
        provider.extract(make_page())

    before = calls["n"]
    with pytest.raises(CircuitOpen):
        provider.extract(make_page(b"another-page"))

    assert calls["n"] == before, "circuit was open; no further calls should be made"


def test_missing_api_key_raises_rather_than_returning_nothing():
    provider = GeminiVisionHTRProvider(api_key=None, transport=None, max_attempts=1,
                                       sleep=lambda s: None)
    with pytest.raises(HTRExtractionError):
        provider.extract(make_page())


def test_blank_page_is_flagged_not_silently_passed_on():
    provider = GeminiVisionHTRProvider(
        api_key="t", transport=transport_returning(json.dumps({"lines": []}))
    )
    page = provider.extract(make_page())

    assert page.lines == ()
    assert page.page_confidence is None
    assert any("MANDATORY_HUMAN" in w for w in page.warnings)
    assert any("BLANK_PAGE" in w for w in page.warnings)


# ---------------------------------------------------------------------------
# GATE (f): replay resolves from cache, never the network
# ---------------------------------------------------------------------------


def test_second_extraction_hits_the_cache_and_does_not_call_the_api(tmp_path):
    calls = {"n": 0}

    def counting(image_bytes, prompt):
        calls["n"] += 1
        return GOOD_RESPONSE

    cache = FilesystemExtractionCache(tmp_path / "cache")
    provider = GeminiVisionHTRProvider(api_key="t", transport=counting, cache=cache)
    page_image = make_page()

    first = provider.extract(page_image)
    second = provider.extract(page_image)

    assert calls["n"] == 1, "second extraction called the API"
    assert first.extraction_sha256 == second.extraction_sha256


def test_replay_with_network_denied_resolves_entirely_from_cache(tmp_path):
    """Network access is actively poisoned, not merely unused."""
    def exploding(image_bytes, prompt):
        raise AssertionError(
            "the network was called during a replay: that is a second "
            "experiment, not a reproduction"
        )

    cache = FilesystemExtractionCache(tmp_path / "cache")
    populate = GeminiVisionHTRProvider(
        api_key="t", transport=transport_returning(GOOD_RESPONSE), cache=cache
    )
    page_image = make_page()
    original = populate.extract(page_image)

    replay = GeminiVisionHTRProvider(api_key=None, transport=exploding, cache=cache)
    replayed = replay.extract(page_image)

    assert replayed.extraction_sha256 == original.extraction_sha256
    assert replayed.text == original.text
    assert replayed.model_id == original.model_id
    assert replayed.prompt_version == original.prompt_version


def test_cache_key_changes_with_model_or_prompt_version():
    """A different model or prompt is a different extraction."""
    base = cache_key("abc", "gemini-3.5-flash", "transcribe/1.0.0")
    assert base != cache_key("abc", "gemini-2.5-pro", "transcribe/1.0.0")
    assert base != cache_key("abc", "gemini-3.5-flash", "transcribe/1.1.0")
    assert base != cache_key("def", "gemini-3.5-flash", "transcribe/1.0.0")


def test_cache_miss_raises_on_require_rather_than_returning_none(tmp_path):
    cache = FilesystemExtractionCache(tmp_path / "cache")
    with pytest.raises(CacheMiss, match="second experiment"):
        cache.require("nothing-stored-here")


def test_cache_stores_the_raw_response_as_the_audit_record(tmp_path):
    cache = FilesystemExtractionCache(tmp_path / "cache")
    provider = GeminiVisionHTRProvider(
        api_key="t", transport=transport_returning(GOOD_RESPONSE), cache=cache
    )
    page_image = make_page()
    provider.extract(page_image)

    key = cache_key(page_image.page_sha256, "gemini-3.5-flash", TRANSCRIPTION_PROMPT_VERSION)
    record = cache.require(key)

    assert record["raw_response"] == GOOD_RESPONSE
    assert record["stored_at"]
    assert record["page"]["model_id"] == "gemini-3.5-flash"


# ---------------------------------------------------------------------------
# GATE (g): identity masking
# ---------------------------------------------------------------------------


def test_masking_without_a_configured_region_refuses_to_send():
    page = make_page()
    with pytest.raises(IdentityMaskError, match="no identity mask region configured"):
        mask_identity_region(page, None)


def test_mask_region_rejects_pixel_coordinates():
    """Fractions only: pixels silently mask the wrong area at another DPI."""
    with pytest.raises(ValueError, match="fraction of the page"):
        MaskRegion(0, 0, 400, 120)


def test_mask_region_rejects_an_inverted_rectangle():
    with pytest.raises(ValueError, match="empty or inverted"):
        MaskRegion(0.5, 0.5, 0.2, 0.6)


def test_masking_changes_the_page_hash():
    """A masked page is a different artefact and must not share a cache entry."""
    pytest.importorskip("PIL")
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(buf, format="PNG")
    page = make_page(buf.getvalue())

    masked = mask_identity_region(page, MaskRegion(0.0, 0.0, 1.0, 0.25))

    assert masked.page_sha256 != page.page_sha256
    assert masked.source_sha256 == page.source_sha256


def _render_page_with_roll_number(roll: str = "CS2024007"):
    """A synthetic answer-sheet page with a known roll number in the header."""
    from PIL import Image, ImageDraw
    import io

    image = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 15), f"Roll No: {roll}", fill="black")
    draw.text((20, 40), "Name: A Student", fill="black")
    draw.text((20, 200), "Q1. Photosynthesis occurs in the chloroplast.", fill="black")

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return make_page(buf.getvalue())


def _ink_pixels(image_bytes: bytes, box):
    """Count non-white pixels in a box. Extraction from the image itself."""
    from PIL import Image
    import io

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    crop = image.crop(box)
    return sum(1 for px in crop.getdata() if px != (255, 255, 255))


def _distinct_colours(image_bytes: bytes, box):
    """Every distinct colour in a box.

    The mask fills solid black, so counting "non-white" pixels is useless here
    -- a correct mask maximises that count. A correctly masked region contains
    exactly ONE colour; any residual glyph would introduce a second.
    """
    from PIL import Image
    import io

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return set(image.crop(box).getdata())


def test_masking_removes_every_ink_pixel_from_the_identity_region():
    """GATE (g), pixel-extraction half.

    Verified by reading pixels back out of the sent image, not by looking at
    it. If any ink survives in the region, some of the roll number survived.

    This is NOT the full gate. The stated requirement is to OCR the masked
    region and assert the number is absent; no OCR engine is installed on this
    machine (no tesseract binary, easyocr absent) and no GEMINI_API_KEY is
    available to use the vision model for it. Zero ink pixels is a strictly
    stronger condition than "OCR reads nothing" -- OCR cannot recover text from
    a region with no ink -- but it does not exercise the same code path, so the
    gate is reported PARTIAL rather than passed.
    """
    pytest.importorskip("PIL")
    page = _render_page_with_roll_number()
    header = (0, 0, 800, 100)

    assert len(_distinct_colours(page.image_bytes, header)) > 1, (
        "test setup: the header must contain glyphs before masking"
    )

    masked = mask_identity_region(page, MaskRegion(0.0, 0.0, 1.0, 0.25, label="header"))

    colours = _distinct_colours(masked.image_bytes, header)
    assert colours == {(0, 0, 0)}, (
        f"masked identity region is not uniform: {len(colours)} distinct colours "
        f"remain ({sorted(colours)[:4]}). Any second colour is a surviving glyph "
        "from the roll number or name."
    )


def test_masking_leaves_the_answer_body_untouched():
    """A mask that eats the answer is as bad as one that misses the header."""
    pytest.importorskip("PIL")
    page = _render_page_with_roll_number()
    body = (0, 150, 800, 400)

    before = _ink_pixels(page.image_bytes, body)
    masked = mask_identity_region(page, MaskRegion(0.0, 0.0, 1.0, 0.25))
    after = _ink_pixels(masked.image_bytes, body)

    assert before > 0
    assert after == before, "masking altered the answer region"


# ---------------------------------------------------------------------------
# The section 2.5 boundary, enforced at the provider
# ---------------------------------------------------------------------------


def test_unmasked_page_is_refused_before_any_network_call():
    """The defect this guard exists for.

    scripts/regenerate_cache.py called provider._invoke() on a raw
    rasterization and sent a real student's name and roll number to Google.
    The boundary lived only in htr_pipeline.extract_script, so any caller
    reaching the provider directly walked around it.
    """
    called = {"n": 0}

    def counting(image_bytes, prompt):
        called["n"] += 1
        return GOOD_RESPONSE

    provider = GeminiVisionHTRProvider(api_key="t", transport=counting)

    with pytest.raises(HTRExtractionError, match="refusing to transmit an unmasked page"):
        provider.extract(make_page(masked=False))

    assert called["n"] == 0, "the image reached the transport despite being unmasked"


def test_unmasked_send_requires_an_explicit_opt_in():
    provider = GeminiVisionHTRProvider(
        api_key="t", transport=transport_returning(GOOD_RESPONSE), allow_unmasked=True
    )
    page = provider.extract(make_page(masked=False))
    assert len(page.lines) == 2


def test_mask_identity_region_marks_the_page_as_masked():
    pytest.importorskip("PIL")
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(buf, format="PNG")
    raw = make_page(buf.getvalue(), masked=False)

    assert raw.identity_masked is False
    assert mask_identity_region(raw, MaskRegion(0.0, 0.0, 1.0, 0.25)).identity_masked is True

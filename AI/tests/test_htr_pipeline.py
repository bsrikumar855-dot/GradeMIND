"""Wiring: provider by config, confidence propagation, no silent empty text."""

from __future__ import annotations

import json

import pytest

from AI.ocr.htr_pipeline import (
    DEFAULT_CONFIDENCE_FLOOR,
    HTRUnavailable,
    build_provider,
    extract_script,
)
from AI.ocr.identity_mask import MaskRegion
from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider


def _scan_path():
    from pathlib import Path
    candidates = sorted(
        Path("backend/storage/answer_sheets").rglob("*.pdf"),
        key=lambda p: p.stat().st_size, reverse=True,
    )
    if not candidates or candidates[0].stat().st_size < 100_000:
        pytest.fail("the real scanned PDF fixture is missing from backend/storage")
    return str(candidates[0])


def transport(payload):
    def _t(image_bytes, prompt):
        return payload
    return _t


LEGIBLE = json.dumps({"lines": [
    {"text": "Q1. Photosynthesis occurs in the chloroplast.", "legibility": 0.93,
     "bbox": [0.1, 0.2, 0.9, 0.24], "script": "Latin"}]})

ILLEGIBLE = json.dumps({"lines": [
    {"text": "Q1. [ILLEGIBLE]", "legibility": 0.31,
     "bbox": [0.1, 0.2, 0.9, 0.24], "script": "Latin"}]})


def test_provider_is_selected_by_config_not_hardcoded(monkeypatch):
    monkeypatch.setenv("HTR_PROVIDER", "none")
    assert build_provider() is None

    monkeypatch.setenv("HTR_PROVIDER", "gemini_vision")
    assert isinstance(build_provider(api_key="t"), GeminiVisionHTRProvider)

    monkeypatch.setenv("HTR_PROVIDER", "wat")
    with pytest.raises(HTRUnavailable, match="unknown HTR_PROVIDER"):
        build_provider()


def test_tesseract_says_it_is_not_wired_rather_than_pretending():
    with pytest.raises(HTRUnavailable, match="not wired"):
        build_provider("tesseract")


def test_provider_none_raises_on_a_scan_instead_of_empty_text():
    with pytest.raises(HTRUnavailable, match="MANDATORY_HUMAN"):
        extract_script(_scan_path(), provider=None, mask_region=MaskRegion(0, 0, 1, 0.2))


def test_unmasked_send_is_refused_by_default():
    from AI.ocr.identity_mask import IdentityMaskError
    provider = GeminiVisionHTRProvider(api_key="t", transport=transport(LEGIBLE))
    with pytest.raises(IdentityMaskError, match="no identity mask region"):
        extract_script(_scan_path(), provider, mask_region=None, dpi=72, max_pages=1)


def test_low_legibility_sets_below_floor_and_blocks_auto():
    provider = GeminiVisionHTRProvider(api_key="t", transport=transport(ILLEGIBLE))
    result = extract_script(
        _scan_path(), provider, mask_region=MaskRegion(0, 0, 1, 0.2), dpi=72, max_pages=2
    )
    assert result.lowest_page_confidence == pytest.approx(0.31)
    assert result.below_confidence_floor is True
    assert result.can_be_auto() is False


def test_high_legibility_still_cannot_be_auto():
    """AUTO is off at config level and the threshold is uncalibrated."""
    provider = GeminiVisionHTRProvider(api_key="t", transport=transport(LEGIBLE))
    result = extract_script(
        _scan_path(), provider, mask_region=MaskRegion(0, 0, 1, 0.2), dpi=72, max_pages=2
    )
    assert result.lowest_page_confidence > DEFAULT_CONFIDENCE_FLOOR
    assert result.below_confidence_floor is False
    assert result.uncalibrated is True
    assert result.can_be_auto() is False


def test_provenance_carries_every_version_field():
    provider = GeminiVisionHTRProvider(api_key="t", transport=transport(LEGIBLE))
    result = extract_script(
        _scan_path(), provider, mask_region=MaskRegion(0, 0, 1, 0.2), dpi=72, max_pages=1
    )
    p = result.provenance()
    for field in ("provider", "model_id", "prompt_version", "rasterize_version",
                  "pipeline_version", "source_sha256", "uncalibrated"):
        assert p.get(field) is not None, f"missing provenance field {field}"


def test_extracted_script_exposes_no_marking_api():
    """Structural: the HTR layer must not be able to award anything."""
    from AI.ocr import htr_pipeline
    for name in dir(htr_pipeline.ExtractedScript):
        if name.startswith("_"):
            continue
        for banned in ("mark", "score", "grade", "award", "assess"):
            assert banned not in name.lower(), f"ExtractedScript.{name} looks like marking"

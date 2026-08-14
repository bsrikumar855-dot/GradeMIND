"""Tests for local HTR providers and fallback chain rules."""

from __future__ import annotations

import io
import json
import pytest
from PIL import Image, ImageDraw

from AI.ocr.htr_pipeline import (
    HTRUnavailable,
    build_fallback_chain,
    build_provider,
    extract_script,
)
from AI.ocr.identity_mask import MaskRegion
from AI.ocr.providers.base import HTRExtractionError, HTRProvider, Line, Page
from AI.ocr.providers.trocr_htr import TrOCRHTRProvider
from AI.ocr.providers.surya_htr import SuryaHTRProvider
from AI.ocr.rasterize import PageImage, sha256_bytes


class StubFailingProvider(HTRProvider):
    name = "stub_failing"

    def describe(self):
        return {"provider": self.name}

    def extract(self, page, hints=None):
        raise HTRExtractionError("stub provider failed as expected")


class StubLowConfidenceProvider(HTRProvider):
    name = "stub_low_conf"

    def describe(self):
        return {"provider": self.name}

    def extract(self, page, hints=None):
        return Page(
            lines=(Line(text="Low confidence text", confidence=0.10, bbox=(0.1, 0.1, 0.9, 0.2)),),
            page_confidence=0.10,
            provider=self.name,
            model_id="stub-model",
            prompt_version="v1",
            page_number=page.page_number,
            page_sha256=page.page_sha256,
            extraction_sha256="abc",
            rasterize_version="v1",
        )


class StubHighConfidenceProvider(HTRProvider):
    name = "stub_high_conf"

    def describe(self):
        return {"provider": self.name}

    def extract(self, page, hints=None):
        return Page(
            lines=(Line(text="High confidence text", confidence=0.95, bbox=(0.1, 0.1, 0.9, 0.2)),),
            page_confidence=0.95,
            provider=self.name,
            model_id="stub-model",
            prompt_version="v1",
            page_number=page.page_number,
            page_sha256=page.page_sha256,
            extraction_sha256="xyz",
            rasterize_version="v1",
        )


def _scan_path():
    from pathlib import Path
    candidates = sorted(
        Path("backend/storage/answer_sheets").rglob("*.pdf"),
        key=lambda p: p.stat().st_size, reverse=True,
    )
    if not candidates or candidates[0].stat().st_size < 100_000:
        pytest.fail("the real scanned PDF fixture is missing")
    return str(candidates[0])


def test_build_provider_resolves_local_providers(monkeypatch):
    monkeypatch.setenv("HTR_PROVIDER", "trocr")
    p1 = build_provider()
    assert isinstance(p1, TrOCRHTRProvider)

    monkeypatch.setenv("HTR_PROVIDER", "surya")
    p2 = build_provider()
    assert isinstance(p2, SuryaHTRProvider)


def test_fallback_does_not_fire_on_low_confidence():
    """CRITICAL RULE: Low confidence is a valid finding, NOT a fallback trigger."""
    primary = StubLowConfidenceProvider()
    fallback = StubHighConfidenceProvider()

    script = extract_script(
        _scan_path(),
        providers=[primary, fallback],
        mask_region=MaskRegion(0, 0, 1, 0.2),
        max_pages=1,
    )

    # Primary provider produced a page (even at 0.10 confidence) so fallback was NOT called
    assert len(script.pages) == 1
    assert script.pages[0].provider == "stub_low_conf"
    assert script.pages[0].page_confidence == pytest.approx(0.10)
    assert script.below_confidence_floor is True


def test_fallback_fires_on_provider_failure():
    primary = StubFailingProvider()
    fallback = StubHighConfidenceProvider()

    script = extract_script(
        _scan_path(),
        providers=[primary, fallback],
        mask_region=MaskRegion(0, 0, 1, 0.2),
        max_pages=1,
    )

    assert len(script.pages) == 1
    assert script.pages[0].provider == "stub_high_conf"
    assert script.pages[0].page_confidence == pytest.approx(0.95)


def test_all_providers_failing_raises_extraction_error():
    p1 = StubFailingProvider()
    p2 = StubFailingProvider()

    with pytest.raises(HTRExtractionError, match="all providers in chain failed"):
        extract_script(
            _scan_path(),
            providers=[p1, p2],
            mask_region=MaskRegion(0, 0, 1, 0.2),
            max_pages=1,
        )


def test_provider_failure_produces_no_page():
    provider = StubFailingProvider()
    page_img = PageImage(
        page_number=1,
        image_bytes=b"fake",
        width=100,
        height=100,
        dpi=300,
        source_sha256="src",
        page_sha256="page",
    )
    with pytest.raises(HTRExtractionError):
        provider.extract(page_img)

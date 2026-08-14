"""PDF -> pages -> mask -> provider -> text. Config-driven, no hardcoded provider.

The stage that was missing. It stops at TEXT: the answer string it produces
goes to `ValuePointMatcher` -> `ScoreComputer` exactly as typed text does, and
nothing in this module knows what a mark is.

    HTR_PROVIDER = gemini_vision | tesseract | none

`none` is a real setting, not a disabled state: it means this deployment does
not do handwriting recognition, and a scanned PDF must route to a human. It
raises rather than returning empty text.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from AI.ocr.identity_mask import MaskRegion, mask_identity_region
from AI.ocr.providers.base import HTRExtractionError, HTRProvider, Page
from AI.ocr.providers.cache import ExtractionCache
from AI.ocr.rasterize import (
    RASTERIZE_VERSION,
    PageImage,
    PDFKind,
    classify_pdf,
    rasterize_pdf,
)

logger = logging.getLogger("GradeMIND.HTRPipeline")

PIPELINE_VERSION = "htr-pipeline/1.0.0"

# A page whose transcription is less legible than this cannot be AUTO. It is a
# DOCUMENTED, UNCALIBRATED default: it has never been derived from a labelled
# set, because there is no labelled set. It is deliberately conservative and
# the uncalibrated flag travels with every result that uses it.
DEFAULT_CONFIDENCE_FLOOR = 0.80


class HTRUnavailable(RuntimeError):
    """No provider is configured to read this document."""


@dataclass(frozen=True)
class ExtractedScript:
    """The transcription of a whole script. Still contains no marks."""

    pages: tuple
    provider: str
    model_id: str
    prompt_version: str
    rasterize_version: str
    pipeline_version: str
    source_sha256: str
    lowest_page_confidence: Optional[float]
    confidence_floor: float
    below_confidence_floor: bool
    uncalibrated: bool
    warnings: tuple

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    def provenance(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "rasterize_version": self.rasterize_version,
            "pipeline_version": self.pipeline_version,
            "source_sha256": self.source_sha256,
            "lowest_page_confidence": self.lowest_page_confidence,
            "confidence_floor": self.confidence_floor,
            "below_confidence_floor": self.below_confidence_floor,
            "uncalibrated": self.uncalibrated,
        }

    def can_be_auto(self) -> bool:
        """Always False today, and the reasons are recorded separately.

        AUTO is disabled at config level across the system (CLAUDE.md shipping
        posture) and would additionally be blocked here by an uncalibrated
        threshold or a page under the floor. Keeping all three reasons live
        means enabling AUTO later cannot accidentally turn on a path that only
        one of them was guarding.
        """
        return False


def build_provider(
    name: Optional[str] = None,
    cache: Optional[ExtractionCache] = None,
    **kwargs: Any,
) -> Optional[HTRProvider]:
    """Resolve the provider from config. No hardcoded default anywhere else."""
    resolved = (name or os.environ.get("HTR_PROVIDER") or "none").strip().lower()

    if resolved == "none":
        return None

    if resolved == "gemini_vision":
        from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider

        return GeminiVisionHTRProvider(cache=cache, **kwargs)

    if resolved == "trocr":
        from AI.ocr.providers.trocr_htr import TrOCRHTRProvider

        return TrOCRHTRProvider(cache=cache, **kwargs)

    if resolved == "surya":
        from AI.ocr.providers.surya_htr import SuryaHTRProvider

        return SuryaHTRProvider(cache=cache, **kwargs)

    if resolved == "tesseract":
        raise HTRUnavailable(
            "HTR_PROVIDER=tesseract is not wired to the page-image interface "
            "yet. The legacy Tesseract path in AI/ocr/ocr_manager.py takes "
            "image file paths, not PageImage objects; adapting it is separate "
            "work. Refusing to pretend it is available."
        )

    raise HTRUnavailable(
        f"unknown HTR_PROVIDER {resolved!r}. Expected one of: "
        "gemini_vision, trocr, surya, tesseract, none"
    )


def build_fallback_chain(
    chain_str: Optional[str] = None,
    cache: Optional[ExtractionCache] = None,
) -> List[HTRProvider]:
    """Build list of providers from HTR_FALLBACK_CHAIN env var."""
    raw = chain_str if chain_str is not None else os.environ.get("HTR_FALLBACK_CHAIN", "")
    if not raw.strip():
        primary = build_provider(cache=cache)
        return [primary] if primary is not None else []

    providers = []
    for name in raw.split(","):
        name = name.strip()
        if not name or name == "none":
            continue
        try:
            p = build_provider(name, cache=cache)
            if p is not None:
                providers.append(p)
        except Exception as exc:
            logger.warning("HTR_FALLBACK_CHAIN skipping unavailable provider %s: %s", name, exc)

    return providers


def extract_script(
    pdf_path: str,
    provider: Optional[HTRProvider] = None,
    providers: Optional[List[HTRProvider]] = None,
    mask_region: Optional[MaskRegion] = None,
    dpi: int = 300,
    max_pages: Optional[int] = None,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    require_mask: bool = True,
) -> ExtractedScript:
    """Rasterize, mask, transcribe. Supports provider fallback chain.

    Fallback rules:
      - Fallback fires ONLY on provider unavailability (import error, network, quota, HTRExtractionError).
      - NEVER on low confidence: a low-confidence result routes to MANDATORY_HUMAN.
      - Every page records its actual producing provider.
    """
    classification = classify_pdf(pdf_path)

    if classification.kind is PDFKind.TEXT_LAYER:
        raise HTRUnavailable(
            f"{pdf_path} has a text layer ({classification.font_count} fonts); "
            "use the existing text extraction path rather than paying for HTR."
        )

    # Resolve provider chain
    chain: List[HTRProvider] = []
    if providers:
        chain = list(providers)
    elif provider:
        chain = [provider]
    else:
        chain = build_fallback_chain()

    if not chain:
        raise HTRUnavailable(
            f"{pdf_path} is {classification.kind.value} and no valid HTR provider "
            "is configured. Route to MANDATORY_HUMAN; do not return an empty answer."
        )

    page_images: List[PageImage] = rasterize_pdf(pdf_path, dpi=dpi, max_pages=max_pages)

    pages: List[Page] = []
    warnings: List[str] = []

    for image in page_images:
        prepared = mask_identity_region(image, mask_region, require_region=require_mask)
        page: Optional[Page] = None
        last_exc: Optional[Exception] = None

        for p in chain:
            try:
                # Attempt extraction with provider p
                page = p.extract(prepared)
                # Successful extraction (even if low confidence) -> STOP chain
                # Low confidence is a valid result that routes to MANDATORY_HUMAN, NOT a fallback trigger.
                break
            except (HTRExtractionError, HTRUnavailable, Exception) as exc:
                last_exc = exc
                logger.warning(
                    "HTR_PIPELINE provider %s failed on page %d: %s. Trying fallback if available...",
                    p.name, image.page_number, exc,
                )

        if page is None:
            raise HTRExtractionError(
                f"page {image.page_number}: all providers in chain failed: {last_exc}. "
                "Route to MANDATORY_HUMAN."
            ) from last_exc

        pages.append(page)
        warnings.extend(f"page {page.page_number}: {w}" for w in page.warnings)

    confidences = [p.page_confidence for p in pages if p.page_confidence is not None]
    lowest = min(confidences) if confidences else None
    below_floor = lowest is None or lowest < confidence_floor

    active_provider = chain[0]
    described = active_provider.describe()

    logger.info(
        "HTR_PIPELINE completed path=%s pages=%d provider=%s lowest_conf=%s "
        "below_floor=%s",
        pdf_path, len(pages), described["provider"], lowest, below_floor,
    )

    return ExtractedScript(
        pages=tuple(pages),
        provider=described.get("provider", active_provider.name),
        model_id=described.get("model_id", "unknown"),
        prompt_version=described.get("prompt_version", "unknown"),
        rasterize_version=RASTERIZE_VERSION,
        pipeline_version=PIPELINE_VERSION,
        source_sha256=page_images[0].source_sha256,
        lowest_page_confidence=lowest,
        confidence_floor=confidence_floor,
        below_confidence_floor=below_floor,
        # Always True for this provider: the legibility rating is a model
        # self-report that has never been compared against human transcription.
        uncalibrated=True,
        warnings=tuple(warnings),
    )

"""Surya local HTR provider (Detection + Recognition + Layout).

Full-page handwriting recognition with line detection, bounding boxes, and confidence.

WHAT THIS SENDS OVER THE NETWORK
--------------------------------
ZERO. Local execution only. Model weights loaded locally without network calls at inference time.
"""

from __future__ import annotations

import io
import hashlib
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from AI.ocr.providers.base import (
    HTRExtractionError,
    HTRProvider,
    Line,
    Page,
    extraction_sha256,
)
from AI.ocr.providers.cache import cache_key, page_to_record, record_to_page, ExtractionCache
from AI.ocr.rasterize import PageImage, sha256_bytes

logger = logging.getLogger("GradeMIND.SuryaHTR")

DEFAULT_SURYA_MODEL = "surya-ocr-v0.22.1"
SURYA_PROMPT_VERSION = "surya/1.0.0"


class SuryaHTRProvider(HTRProvider):
    name = "surya"

    def __init__(
        self,
        model_id: str = DEFAULT_SURYA_MODEL,
        weights_sha256: str = "UNAVAILABLE",
        cache: Optional[ExtractionCache] = None,
        langs: Optional[List[str]] = None,
    ):
        self.model_id = model_id
        self.weights_sha256 = weights_sha256
        self.cache = cache
        self.langs = langs or ["en"]

        self._det_model = None
        self._det_processor = None
        self._rec_model = None
        self._rec_processor = None

    def _ensure_loaded(self) -> None:
        """Lazy load surya models once per process."""
        if self._rec_model is not None:
            return

        try:
            from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_proc
            from surya.model.recognition.model import load_model as load_rec_model
            from surya.model.recognition.processor import load_processor as load_rec_proc

            self._det_model = load_det_model()
            self._det_proc = load_det_proc()
            self._rec_model = load_rec_model()
            self._rec_proc = load_rec_proc()
            logger.info("Surya OCR models loaded successfully.")
        except Exception as exc:
            raise HTRExtractionError(
                f"surya-ocr is not available or failed to load ({exc}). "
                "Ensure `surya-ocr` is installed and weights are present."
            ) from exc

    def describe(self) -> Dict[str, str]:
        return {
            "provider": self.name,
            "model_id": self.model_id,
            "weights_sha256": self.weights_sha256,
            "prompt_version": SURYA_PROMPT_VERSION,
            "languages": ",".join(self.langs),
        }

    def extract(self, page: PageImage, hints: Optional[Dict[str, Any]] = None) -> Page:
        key = cache_key(page.page_sha256, self.model_id, SURYA_PROMPT_VERSION)

        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None:
                logger.info("HTR_STAGE cache_hit page=%s key=%s", page.page_number, key[:24])
                return record_to_page(cached)

        # Step 1: Ensure surya is loaded
        self._ensure_loaded()

        try:
            from surya.ocr import run_ocr
            pil_img = Image.open(io.BytesIO(page.image_bytes)).convert("RGB")
        except Exception as exc:
            raise HTRExtractionError(f"page {page.page_number}: cannot decode image for Surya: {exc}") from exc

        width, height = pil_img.size

        try:
            predictions = run_ocr(
                [pil_img],
                [self.langs],
                self._det_model,
                self._det_proc,
                self._rec_model,
                self._rec_proc,
            )
        except Exception as exc:
            raise HTRExtractionError(f"page {page.page_number}: Surya OCR inference failed: {exc}") from exc

        if not predictions or not hasattr(predictions[0], "text_lines"):
            raise HTRExtractionError(f"page {page.page_number}: Surya returned invalid response format.")

        raw_lines = predictions[0].text_lines
        lines: List[Line] = []

        for item in raw_lines:
            text = getattr(item, "text", "").strip()
            confidence = getattr(item, "confidence", None)
            bbox_raw = getattr(item, "bbox", None)

            bbox: Optional[Tuple[float, float, float, float]] = None
            if bbox_raw and len(bbox_raw) == 4:
                x0, y0, x1, y1 = bbox_raw
                bbox = (
                    round(x0 / width, 4),
                    round(y0 / height, 4),
                    round(x1 / width, 4),
                    round(y1 / height, 4),
                )

            lines.append(
                Line(
                    text=text,
                    confidence=float(confidence) if confidence is not None else None,
                    bbox=bbox,
                    script="Latin",
                )
            )

        if not lines:
            raise HTRExtractionError(
                f"page {page.page_number}: Surya produced zero text lines. Route to MANDATORY_HUMAN."
            )

        confidences = [l.confidence for l in lines if l.confidence is not None]
        page_confidence = min(confidences) if confidences else None

        result_page = Page(
            lines=tuple(lines),
            page_confidence=page_confidence,
            provider=self.name,
            model_id=self.model_id,
            prompt_version=SURYA_PROMPT_VERSION,
            page_number=page.page_number,
            page_sha256=page.page_sha256,
            extraction_sha256=extraction_sha256(lines),
            rasterize_version=page.rasterize_version,
            raw_response_sha256=hashlib.sha256(self.weights_sha256.encode("utf-8")).hexdigest(),
        )

        if self.cache is not None:
            self.cache.put(key, page_to_record(result_page, {"weights_sha256": self.weights_sha256}))

        return result_page

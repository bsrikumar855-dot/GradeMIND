"""
GradeMIND TrOCR Handwriting Engine.

Uses microsoft/trocr-base-handwritten via HuggingFace Transformers
to extract text from handwritten answer sheet images.

TrOCR is a Transformer-based OCR model specifically fine-tuned on
handwriting datasets (IAM, IMGUR5K) and significantly outperforms
general-purpose OCR engines on cursive/messy handwriting.

Usage:
    engine = TrOCREngine()
    doc = engine.extract("answer_sheet.jpg", "sub_001")
    print(doc.confidence, [line.text for line in doc.lines])
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Tuple

from AI.schemas.ocr_schema import OCRDocument, OCRLine, OCRRegion

logger = logging.getLogger("GradeMIND.TrOCREngine")

# ─────────────────────────────────────────────────────────────────────────────
# Model singleton — loaded once on first use
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_NAME = "microsoft/trocr-base-handwritten"
_TROCR_READY = False
_processor = None
_model = None


def _init_trocr() -> None:
    """Lazy-load TrOCR processor and model (first call only)."""
    global _TROCR_READY, _processor, _model
    if _TROCR_READY:
        return

    try:
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        logger.info("TrOCR: Loading model %s …", _MODEL_NAME)
        _processor = TrOCRProcessor.from_pretrained(_MODEL_NAME)
        _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
        _model.eval()

        # Move to GPU if available, keep CPU otherwise
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(_device)
        logger.info("TrOCR: Model loaded on %s", _device)
        _TROCR_READY = True

    except Exception as exc:
        logger.warning(
            "TrOCR: Failed to load model %s — engine will be unavailable. Error: %s",
            _MODEL_NAME,
            exc,
        )
        _processor = None
        _model = None
        _TROCR_READY = True  # Mark as attempted so we don't retry on every call


# ─────────────────────────────────────────────────────────────────────────────
# Line segmentation helper
# ─────────────────────────────────────────────────────────────────────────────

def _segment_lines_opencv(image_path: str) -> List[Tuple[object, Tuple[int, int, int, int]]]:
    """
    Use OpenCV morphological operations to detect horizontal text lines.
    Returns list of (line_image_array, (x, y, w, h)) tuples in reading order.

    Falls back to halving the image vertically if OpenCV is not available.
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # OTSU binarisation
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Dilate horizontally to merge words into line-blobs
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        dilated = cv2.dilate(binary, h_kernel, iterations=3)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Sort contours top-to-bottom
        bounding_boxes = sorted(
            [cv2.boundingRect(c) for c in contours],
            key=lambda b: b[1]
        )

        lines = []
        for x, y, w, h in bounding_boxes:
            # Skip tiny noise blobs
            if h < 8 or w < 30:
                continue
            # Add a small vertical margin
            y0 = max(0, y - 4)
            y1 = min(img.shape[0], y + h + 4)
            line_img = img[y0:y1, x:x + w]
            lines.append((line_img, (x, y0, w, y1 - y0)))

        if lines:
            return lines

    except ImportError:
        logger.debug("TrOCR: OpenCV not available for line segmentation; using PIL fallback")
    except Exception as exc:
        logger.warning("TrOCR: Line segmentation failed (%s); falling back", exc)

    # ── PIL fallback: split image into horizontal strips ──────────────────
    try:
        from PIL import Image as PILImage
        import numpy as np

        pil_img = PILImage.open(image_path).convert("RGB")
        arr = np.array(pil_img)
        h, w = arr.shape[:2]
        # Estimate ~5 lines per page; each strip covers 1/5 of the height
        n_strips = min(max(1, h // 80), 30)
        strip_h = h // n_strips
        strips = []
        for i in range(n_strips):
            y0 = i * strip_h
            y1 = min(h, (i + 1) * strip_h)
            strips.append((arr[y0:y1, :, :], (0, y0, w, y1 - y0)))
        return strips

    except Exception as exc2:
        logger.error("TrOCR: All line segmentation strategies failed: %s", exc2)
        return []


def _array_to_pil(arr: "np.ndarray") -> "Image":
    """Convert numpy array (BGR or RGB) to RGB PIL Image."""
    from PIL import Image as PILImage
    import numpy as np
    if arr.ndim == 2:
        # Grayscale — convert to RGB
        return PILImage.fromarray(arr).convert("RGB")
    if arr.shape[2] == 4:
        return PILImage.fromarray(arr, "RGBA").convert("RGB")
    # OpenCV stores as BGR; convert to RGB
    rgb = arr[:, :, ::-1].copy()
    return PILImage.fromarray(rgb.astype(np.uint8))


def _pil_from_path(image_path: str) -> "Image":
    """Load any supported image format as a PIL RGB image."""
    from PIL import Image as PILImage
    return PILImage.open(image_path).convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# TrOCR Engine class
# ─────────────────────────────────────────────────────────────────────────────

class TrOCREngine:
    """
    Handwriting-specialised OCR engine using microsoft/trocr-base-handwritten.

    The engine:
      1. Segments the input image into horizontal text lines using OpenCV
         (PIL strip-fallback when OpenCV is unavailable).
      2. Runs each line image through TrOCR independently.
      3. Aggregates line results into an OCRDocument.

    This architecture mirrors how TrOCR was trained (line-level recognition)
    and produces far better results than passing a full page in one shot.
    """

    def __init__(self) -> None:
        _init_trocr()

    def is_available(self) -> bool:
        return _model is not None and _processor is not None

    # ── Public API ────────────────────────────────────────────────────────

    def extract_text(self, image_path: str) -> str:
        """Return the full plain-text content extracted from *image_path*."""
        doc = self.extract(image_path, submission_id="inline")
        return "\n".join(line.text for line in doc.lines)

    def extract_lines(self, image_path: str) -> List[str]:
        """Return a list of extracted text lines from *image_path*."""
        doc = self.extract(image_path, submission_id="inline")
        return [line.text for line in doc.lines]

    def extract_confidence(self, image_path: str) -> float:
        """Return the aggregate OCR confidence for *image_path* (0.0–1.0)."""
        doc = self.extract(image_path, submission_id="inline")
        return doc.confidence

    def extract(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Full extraction pipeline: segment → recognise → aggregate.

        Args:
            image_path:    Path to the image file (JPG/PNG/PDF converted frame).
            submission_id: Identifier for logging and document association.

        Returns:
            OCRDocument with recognised lines and aggregate confidence.

        Raises:
            RuntimeError: When the TrOCR model failed to load.
            FileNotFoundError: When image_path does not exist.
        """
        if not self.is_available():
            raise RuntimeError(
                "TrOCR engine is unavailable — model failed to load. "
                "Check that transformers and torch are installed, and that "
                f"{_MODEL_NAME} can be downloaded from HuggingFace."
            )

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"TrOCR: Image not found: {image_path}")

        logger.info("TrOCR: Starting extraction submission_id=%s path=%s", submission_id, image_path)

        line_segments = _segment_lines_opencv(image_path)
        if not line_segments:
            logger.warning("TrOCR: No line segments detected for %s; attempting full-page", image_path)
            # Fall back to full-page recognition
            pil_image = _pil_from_path(image_path)
            text, confidence = self._recognise_pil(pil_image)
            if not text.strip():
                return OCRDocument(submission_id=submission_id, confidence=0.0, lines=[], regions=[])
            lines = [OCRLine(text=text.strip(), confidence=confidence, bounding_box=[], top_y=0.0, left_x=0.0)]
            return OCRDocument(submission_id=submission_id, confidence=confidence, lines=lines, regions=[])

        ocr_lines: List[OCRLine] = []
        total_confidence = 0.0

        for idx, (line_arr, (lx, ly, lw, lh)) in enumerate(line_segments):
            try:
                pil_line = _array_to_pil(line_arr)
                text, confidence = self._recognise_pil(pil_line)
                text = text.strip()
                if not text:
                    continue

                bbox = [[float(lx), float(ly)], [float(lx + lw), float(ly)],
                        [float(lx + lw), float(ly + lh)], [float(lx), float(ly + lh)]]

                ocr_lines.append(OCRLine(
                    text=text,
                    confidence=confidence,
                    bounding_box=bbox,
                    top_y=float(ly),
                    left_x=float(lx),
                ))
                total_confidence += confidence
                logger.debug(
                    "TrOCR: line=%d confidence=%.3f text=%r",
                    idx + 1, confidence, text[:60]
                )

            except Exception as exc:
                logger.warning("TrOCR: line %d recognition failed: %s", idx + 1, exc)

        aggregate_confidence = (total_confidence / len(ocr_lines)) if ocr_lines else 0.0
        logger.info(
            "TrOCR: Completed submission_id=%s lines=%d avg_confidence=%.3f",
            submission_id, len(ocr_lines), aggregate_confidence
        )

        return OCRDocument(
            submission_id=submission_id,
            confidence=aggregate_confidence,
            lines=ocr_lines,
            regions=[],
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _recognise_pil(self, pil_image: "Image") -> Tuple[str, float]:
        """
        Run TrOCR inference on a PIL RGB image.

        Returns:
            (recognised_text, pseudo_confidence)
        """
        import torch

        # TrOCR processor expects RGB PIL image
        pixel_values = _processor(images=pil_image, return_tensors="pt").pixel_values
        device = next(_model.parameters()).device
        pixel_values = pixel_values.to(device)

        with torch.no_grad():
            # generate() returns sequence token IDs
            generated_ids = _model.generate(
                pixel_values,
                max_new_tokens=128,
                num_beams=4,         # Beam search for better accuracy
                early_stopping=True,
            )

        text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # TrOCR does not natively emit per-token confidence.
        # We derive a pseudo-confidence from output length and text quality heuristics.
        confidence = self._estimate_confidence(text)
        return text, confidence

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """
        Estimate extraction confidence from the generated text.

        Heuristics:
          - Empty output → 0.0
          - Very short output (<3 chars) → 0.4
          - Contains common OCR garbage characters → penalty
          - Reasonable word content → 0.85 base
        """
        if not text or not text.strip():
            return 0.0
        stripped = text.strip()
        if len(stripped) < 3:
            return 0.4

        # Penalize outputs that are mostly non-alphanumeric (OCR garbage)
        alnum_ratio = sum(c.isalnum() or c.isspace() for c in stripped) / len(stripped)
        if alnum_ratio < 0.5:
            return 0.45

        # Penalize if most characters are the same (hallucination pattern)
        most_common_char_ratio = max(stripped.count(c) for c in set(stripped)) / len(stripped)
        if most_common_char_ratio > 0.6:
            return 0.50

        # Base confidence for clean output
        return round(min(0.92, 0.75 + alnum_ratio * 0.15), 3)

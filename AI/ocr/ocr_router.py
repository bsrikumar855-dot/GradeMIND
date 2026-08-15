"""
GradeMIND OCR Router.

Intelligently routes answer-sheet images to the best OCR engine based on:
  1. Content-type detection (printed vs handwritten)
  2. Engine availability (TrOCR, EasyOCR, PaddleOCR, Tesseract)
  3. Confidence fallback (if confidence < threshold → Gemini Vision)

Routing logic:
  ┌─────────────────────────────────────────────────────────────┐
  │  Image Input                                                │
  │       │                                                     │
  │  Classify (on raw image): printed | handwritten | mixed     │
  │       │                                                     │
  │  Preprocess per engine attempted (see preprocess.py          │
  │  ENGINE_PREPROCESS_PROFILES: Tesseract binarises, neural     │
  │  engines get deskew+CLAHE+denoise only)                      │
  │       │                                                     │
  │  ┌────┴──────────────────────────────────────┐             │
  │  │ printed        │ handwritten  │ mixed       │             │
  │  ▼                ▼              ▼             │             │
  │  EasyOCR     TrOCR          EasyOCR +         │             │
  │                              TrOCR (vote)      │             │
  │  └────┬──────────────────────────────────────┘             │
  │       │                                                     │
  │  confidence ≥ 0.70?  →  Return result                      │
  │  confidence  < 0.70?  →  Gemini Vision fallback             │
  └─────────────────────────────────────────────────────────────┘

Usage:
    router = OCRRouter()
    doc = router.route(image_path="answer_sheet.jpg", submission_id="s001")
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Optional

from AI.schemas.ocr_schema import OCRDocument, OCRLine

logger = logging.getLogger("GradeMIND.OCRRouter")

# Confidence threshold below which Gemini Vision is triggered
_GEMINI_FALLBACK_THRESHOLD = 0.70
# Minimum text length below which we consider the result empty
_MIN_TEXT_LENGTH = 10


class ContentType(str, Enum):
    PRINTED = "printed"
    HANDWRITTEN = "handwritten"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Content-type classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify_content_type(image_path: str) -> ContentType:
    """
    Heuristically classify whether the image contains printed or handwritten text.

    Strategy:
      - Compute the ratio of connected-component sizes in the binarised image.
      - Printed text has highly uniform, small, rectangular components.
      - Handwriting has larger, more irregularly shaped components.

    Falls back to UNKNOWN when OpenCV is unavailable.

    Args:
        image_path: Path to the image file.

    Returns:
        ContentType enum value.
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return ContentType.UNKNOWN

        # Binarise
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

        if num_labels <= 1:
            return ContentType.UNKNOWN

        # stats columns: LEFT, TOP, WIDTH, HEIGHT, AREA
        areas = stats[1:, cv2.CC_STAT_AREA]   # Skip background (label 0)
        widths = stats[1:, cv2.CC_STAT_WIDTH]
        heights = stats[1:, cv2.CC_STAT_HEIGHT]

        if len(areas) == 0:
            return ContentType.UNKNOWN

        # Filter out large blocks (margins, borders) and tiny noise
        h_img, w_img = img.shape
        char_mask = (areas > 10) & (areas < (h_img * w_img * 0.05))
        if not np.any(char_mask):
            return ContentType.UNKNOWN

        char_areas = areas[char_mask]
        char_widths = widths[char_mask]
        char_heights = heights[char_mask]

        # Key metrics
        area_cv = float(np.std(char_areas) / (np.mean(char_areas) + 1e-6))   # Coeff. of variation
        aspect_mean = float(np.mean(char_widths / (char_heights + 1e-6)))
        n_components = len(char_areas)

        logger.debug(
            "ContentType: n_components=%d area_cv=%.3f aspect_mean=%.3f",
            n_components, area_cv, aspect_mean,
        )

        # Printed text: low area variance (uniform), moderate aspect ratio
        # Handwriting: high area variance, irregular aspect
        if area_cv < 0.6 and 0.3 < aspect_mean < 3.0:
            return ContentType.PRINTED
        elif area_cv > 1.2 or aspect_mean > 3.5:
            return ContentType.HANDWRITTEN
        else:
            return ContentType.MIXED

    except ImportError:
        logger.debug("ContentType: OpenCV unavailable — returning UNKNOWN")
        return ContentType.UNKNOWN
    except Exception as exc:
        logger.warning("ContentType: Classification failed (%s); returning UNKNOWN", exc)
        return ContentType.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Gemini Vision fallback
# ─────────────────────────────────────────────────────────────────────────────

def _gemini_vision_ocr(image_path: str, submission_id: str) -> Optional[OCRDocument]:
    """
    Call the Gemini Vision API to extract text when local OCR confidence is low.

    Requires GEMINI_API_KEY environment variable.

    Args:
        image_path:    Path to image file.
        submission_id: Logging reference.

    Returns:
        OCRDocument on success, None on failure or missing API key.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.info("Gemini Vision fallback skipped: GEMINI_API_KEY not set")
        return None

    try:
        import google.generativeai as genai
        from PIL import Image as PILImage

        # Imported, never re-typed. This site previously hardcoded its own
        # model string, so a pin change in the provider left this path calling
        # a different model -- two models in one pipeline, with only one of
        # them recorded on the result. That is the same defect class as the
        # silent embedding fallback removed in Phase 0 item 1.2: a second code
        # path quietly deciding something the provenance record claims is
        # fixed.
        from AI.ocr.providers.gemini_vision import DEFAULT_MODEL_ID

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(DEFAULT_MODEL_ID)

        pil_image = PILImage.open(image_path).convert("RGB")

        prompt = (
            "You are an expert OCR system specialising in handwritten exam answer sheets. "
            "Extract ALL text from this image exactly as written, preserving line breaks. "
            "Include question numbers if visible. "
            "Do NOT add any explanation, formatting, or markdown — only the raw text."
        )
        response = model.generate_content(
            [prompt, pil_image],
            generation_config=genai.types.GenerationConfig(temperature=0.0),
            request_options={"timeout": 30},
        )

        raw_text = response.text.strip()
        if not raw_text:
            logger.warning("Gemini Vision: returned empty text for %s", image_path)
            return None

        # Build OCRDocument from Gemini response
        lines = []
        for idx, line_text in enumerate(raw_text.splitlines()):
            stripped = line_text.strip()
            if stripped:
                lines.append(OCRLine(
                    text=stripped,
                    confidence=0.88,   # Gemini is generally reliable for this task
                    bounding_box=[],
                    top_y=float(idx),
                    left_x=0.0,
                ))

        doc = OCRDocument(
            submission_id=submission_id,
            confidence=0.88 if lines else 0.0,
            lines=lines,
            regions=[],
        )
        logger.info(
            "Gemini Vision fallback: extracted %d lines from %s",
            len(lines), image_path,
        )
        return doc

    except Exception as exc:
        logger.error("Gemini Vision fallback failed for %s: %s", image_path, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# OCR Router
# ─────────────────────────────────────────────────────────────────────────────

class OCRRouter:
    """
    Routes an answer-sheet image to the optimal OCR engine.

    Engine priority by content type:
      - PRINTED     → EasyOCR (fast, accurate for printed text)
      - HANDWRITTEN → TrOCR   (fine-tuned on handwriting datasets)
      - MIXED       → TrOCR first, EasyOCR as tiebreaker
      - UNKNOWN     → TrOCR first, then EasyOCR, then Tesseract

    Fallback chain:
      Primary engine fails or confidence < 0.70 → next engine
      All local engines fail or confidence < 0.70 → Gemini Vision
    """

    def __init__(
        self,
        confidence_threshold: float = _GEMINI_FALLBACK_THRESHOLD,
        preprocess: bool = True,
        force_engine: Optional[str] = None,
    ) -> None:
        """
        Args:
            confidence_threshold: Minimum acceptable confidence before triggering Gemini fallback.
            preprocess:           Whether to apply image preprocessing before OCR.
            force_engine:         Force a specific engine: "trocr" | "easyocr" | "paddle" | "tesseract".
        """
        self.confidence_threshold = confidence_threshold
        self.preprocess = preprocess
        self.force_engine = force_engine

        # Lazy engine imports — only instantiate what's needed
        self._trocr: Optional[object] = None
        self._easyocr: Optional[object] = None
        self._paddle: Optional[object] = None
        self._tesseract: Optional[object] = None

    # ── Public API ────────────────────────────────────────────────────────

    def route(self, image_path: str, submission_id: str) -> OCRDocument:
        """
        Route an image through the best available OCR engine.

        Args:
            image_path:    Path to the answer-sheet image.
            submission_id: Submission identifier for logging.

        Returns:
            OCRDocument with the best available extraction result.

        Raises:
            RuntimeError: When all OCR engines and the Gemini fallback fail.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"OCRRouter: image not found: {image_path}")

        # ── Step 1: Classify content type (always on the original image) ──
        content_type = ContentType.UNKNOWN if self.force_engine else classify_content_type(image_path)

        logger.info(
            "OCRRouter: submission_id=%s content_type=%s force_engine=%s",
            submission_id, content_type, self.force_engine,
        )

        # ── Step 2: Build engine priority list ───────────────────────────
        engine_order = self._build_engine_order(content_type)

        # ── Step 3: Try engines in order, preprocessing per-engine ────────
        # Each engine gets a preprocessing profile tuned to it (see
        # AI/ocr/preprocess.py ENGINE_PREPROCESS_PROFILES) — e.g. Tesseract
        # wants a hard-binarised image, neural engines want plain grayscale.
        # Results are cached per profile so engines sharing a profile don't
        # redo the same preprocessing work.
        best_doc: Optional[OCRDocument] = None
        last_error: Optional[Exception] = None
        preprocessed_cache: dict = {}

        for engine_name in engine_order:
            working_path = self._preprocess_for(image_path, engine_name, preprocessed_cache)
            try:
                doc = self._run_engine(engine_name, working_path, submission_id)
                text_len = sum(len(l.text) for l in doc.lines)
                logger.info(
                    "OCRRouter: engine=%s confidence=%.3f lines=%d chars=%d",
                    engine_name, doc.confidence, len(doc.lines), text_len,
                )

                if best_doc is None or doc.confidence > best_doc.confidence:
                    best_doc = doc

                # Accept result if it meets the threshold
                if doc.confidence >= self.confidence_threshold and text_len >= _MIN_TEXT_LENGTH:
                    logger.info(
                        "OCRRouter: accepted engine=%s confidence=%.3f submission_id=%s",
                        engine_name, doc.confidence, submission_id,
                    )
                    return doc

            except Exception as exc:
                last_error = exc
                logger.warning("OCRRouter: engine=%s failed: %s", engine_name, exc)

        # ── Step 4: Gemini Vision fallback ────────────────────────────────
        if best_doc is None or best_doc.confidence < self.confidence_threshold:
            logger.info(
                "OCRRouter: confidence=%.3f below threshold=%.2f; trying Gemini Vision",
                best_doc.confidence if best_doc else 0.0,
                self.confidence_threshold,
            )
            gemini_doc = _gemini_vision_ocr(image_path, submission_id)  # Use original (not preprocessed)
            if gemini_doc and gemini_doc.lines:
                return gemini_doc

        # ── Step 5: Return best available or raise ────────────────────────
        if best_doc and best_doc.lines:
            logger.warning(
                "OCRRouter: returning low-confidence result confidence=%.3f submission_id=%s",
                best_doc.confidence, submission_id,
            )
            return best_doc

        raise RuntimeError(
            f"OCRRouter: all engines failed for submission {submission_id}. "
            f"Last error: {last_error}"
        )

    def detect_content_type(self, image_path: str) -> str:
        """Public accessor for content-type classification. Returns string value."""
        return classify_content_type(image_path).value

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_engine_order(self, content_type: ContentType) -> list[str]:
        """Return the ordered list of engine names to try for a content type."""
        if self.force_engine:
            # User-specified override — still allow fallback to others
            others = [e for e in ["trocr", "easyocr", "paddle", "tesseract"]
                      if e != self.force_engine]
            return [self.force_engine] + others

        order_map = {
            ContentType.PRINTED:     ["easyocr", "paddle", "trocr", "tesseract"],
            ContentType.HANDWRITTEN: ["trocr", "easyocr", "paddle", "tesseract"],
            ContentType.MIXED:       ["trocr", "easyocr", "paddle", "tesseract"],
            ContentType.UNKNOWN:     ["trocr", "easyocr", "paddle", "tesseract"],
        }
        return order_map.get(content_type, ["trocr", "easyocr", "paddle", "tesseract"])

    def _run_engine(self, engine_name: str, image_path: str, submission_id: str) -> OCRDocument:
        """Dispatch to named engine and return its OCRDocument."""
        if engine_name == "trocr":
            return self._get_trocr().extract(image_path, submission_id)
        elif engine_name == "easyocr":
            return self._get_easyocr().extract(image_path, submission_id)
        elif engine_name == "paddle":
            return self._get_paddle().extract(image_path, submission_id)
        elif engine_name == "tesseract":
            return self._get_tesseract().extract(image_path, submission_id)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    def _get_trocr(self):
        if self._trocr is None:
            from AI.ocr.trocr_engine import TrOCREngine
            self._trocr = TrOCREngine()
        return self._trocr

    def _get_easyocr(self):
        if self._easyocr is None:
            from AI.ocr.easyocr_engine import EasyOCREngine
            self._easyocr = EasyOCREngine()
        return self._easyocr

    def _get_paddle(self):
        if self._paddle is None:
            from AI.ocr.paddle_engine import PaddleOCREngine
            self._paddle = PaddleOCREngine()
        return self._paddle

    def _get_tesseract(self):
        if self._tesseract is None:
            from AI.ocr.tesseract_engine import TesseractOCREngine
            self._tesseract = TesseractOCREngine()
        return self._tesseract

    def _preprocess_for(self, image_path: str, engine_name: str, cache: dict) -> str:
        """
        Return the preprocessed image path for *engine_name*, using the
        engine's tuned profile (see preprocess_for_engine). Results are
        cached per-profile within a single route() call.
        """
        if not self.preprocess:
            return image_path

        from AI.ocr.preprocess import ENGINE_PREPROCESS_PROFILES, preprocess_for_engine
        profile_key = engine_name if engine_name in ENGINE_PREPROCESS_PROFILES else "tesseract"
        if profile_key in cache:
            return cache[profile_key]

        try:
            working_path = preprocess_for_engine(image_path, profile_key, do_perspective=False)
        except Exception as exc:
            logger.warning("OCRRouter: preprocessing failed for engine=%s (%s); using original image", engine_name, exc)
            working_path = image_path

        cache[profile_key] = working_path
        return working_path

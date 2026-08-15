"""Non-Text Content Classification — detecting diagrams, tables, equations, struck-out text, and non-Latin script.

A SEPARATE Gemini Vision call from transcription and segmentation.

ROUTING RULE
------------
Any flag set -> the question routes to MANDATORY_HUMAN. The marking engine does not score it
at all — not partially, not "the text portion only". A 5-mark question with 3 marks in a diagram
cannot be scored from its text.
"""

from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai
from PIL import Image

from AI.ocr.providers.cache import ExtractionCache, cache_key, page_to_record, record_to_page
from AI.ocr.rasterize import PageImage, sha256_bytes
from AI.ocr.segmentation import QuestionRegion

logger = logging.getLogger("GradeMIND.ContentClassifier")

CLASSIFIER_PROMPT_VERSION = "content-classifier/1.0.0"
DEFAULT_CLASSIFIER_MODEL = "gemini-2.0-flash"


class ContentClassifierError(RuntimeError):
    """Content classification failed.

    Raised rather than returning partial or unflagged content.
    """


class OfflineCacheMissError(ContentClassifierError):
    """Raised when offline mode is requested but a cache miss occurs."""


@dataclass(frozen=True)
class ContentFlags:
    """Non-text content detection flags."""

    contains_diagram: bool = False
    contains_table: bool = False
    contains_equation: bool = False
    contains_struck_out: bool = False
    non_latin_script: bool = False

    @property
    def has_flags(self) -> bool:
        return any((
            self.contains_diagram,
            self.contains_table,
            self.contains_equation,
            self.contains_struck_out,
            self.non_latin_script,
        ))

    def flagged_reasons(self) -> Tuple[str, ...]:
        reasons = []
        if self.contains_diagram:
            reasons.append("CONTAINS_DIAGRAM")
        if self.contains_table:
            reasons.append("CONTAINS_TABLE")
        if self.contains_equation:
            reasons.append("CONTAINS_EQUATION")
        if self.contains_struck_out:
            reasons.append("CONTAINS_STRUCK_OUT")
        if self.non_latin_script:
            reasons.append("NON_LATIN_SCRIPT")
        return tuple(reasons)


CONTENT_CLASSIFIER_PROMPT = """\
You are an expert examination answer script classifier.

Analyze the handwritten answer script image carefully. Detect any non-text or special content structures present on the page.

BIASED TOWARD FALSE POSITIVES: If you are uncertain whether a drawing is a diagram or whether notation is a complex equation, set the flag to true.

Flags to evaluate:
- "contains_diagram": hand-drawn diagrams, flowcharts, graphs, illustrations, circuit diagrams, or schematics.
- "contains_table": tables, grids, tabular columns/rows of data or text.
- "contains_equation": complex mathematical or chemical formulas/notation beyond simple arithmetic (e.g. integrals, matrices, fractions, organic chemistry structures).
- "contains_struck_out": crossed-out, scribbled-over, or struck-through lines of writing.
- "non_latin_script": non-Latin script handwriting (e.g. Devanagari, Hindi, Tamil, Arabic).

Return only JSON matching the schema:
{
  "contains_diagram": boolean,
  "contains_table": boolean,
  "contains_equation": boolean,
  "contains_struck_out": boolean,
  "non_latin_script": boolean
}"""


CONTENT_CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "contains_diagram": {"type": "boolean"},
        "contains_table": {"type": "boolean"},
        "contains_equation": {"type": "boolean"},
        "contains_struck_out": {"type": "boolean"},
        "non_latin_script": {"type": "boolean"},
    },
    "required": [
        "contains_diagram",
        "contains_table",
        "contains_equation",
        "contains_struck_out",
        "non_latin_script",
    ],
}


class ContentClassifier:
    """Classify non-text content in page images via Gemini Vision."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: str = DEFAULT_CLASSIFIER_MODEL,
        cache: Optional[ExtractionCache] = None,
        timeout: float = 120.0,
        offline: bool = False,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key and not offline:
            from dotenv import load_dotenv
            from pathlib import Path
            env_path = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
            self.api_key = os.environ.get("GEMINI_API_KEY")

        self.model_id = model_id
        self.cache = cache
        self.timeout = timeout
        self.offline = offline

        if self.api_key:
            genai.configure(api_key=self.api_key)

    def describe(self) -> Dict[str, str]:
        return {
            "classifier": "gemini_vision_classifier",
            "model_id": self.model_id,
            "prompt_version": CLASSIFIER_PROMPT_VERSION,
            "offline": str(self.offline),
        }

    def classify_page(self, page: PageImage) -> ContentFlags:
        """Classify a single PageImage for non-text content.

        Enforces mandatory cache check. If offline=True and cache miss occurs,
        raises OfflineCacheMissError.
        """
        key = cache_key(page.page_sha256, f"classifier_{self.model_id}", CLASSIFIER_PROMPT_VERSION)

        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None and "flags" in cached:
                logger.info("CONTENT_CLASSIFIER cache_hit page=%d model_id=%s key=%s", page.page_number, self.model_id, key[:16])
                f_dict = cached["flags"]
                return ContentFlags(**f_dict)

        if self.offline:
            logger.error("OFFLINE MODE: Cache miss for page=%d model_id=%s key=%s", page.page_number, self.model_id, key[:16])
            raise OfflineCacheMissError(
                f"Offline mode enabled: cache miss for page {page.page_number} with model {self.model_id}. Network calls forbidden."
            )

        if not self.api_key:
            raise ContentClassifierError(
                f"page {page.page_number}: GEMINI_API_KEY is not set for ContentClassifier model={self.model_id}."
            )

        try:
            image = Image.open(io.BytesIO(page.image_bytes))
        except Exception as exc:
            raise ContentClassifierError(f"page {page.page_number}: invalid image bytes: {exc}") from exc

        model = genai.GenerativeModel(
            model_name=self.model_id,
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
                "response_schema": CONTENT_CLASSIFIER_SCHEMA,
            },
        )

        attempts = 0
        max_attempts = 2
        raw_text = None

        while attempts < max_attempts:
            attempts += 1
            try:
                response = model.generate_content(
                    [CONTENT_CLASSIFIER_PROMPT, image],
                    request_options={"timeout": self.timeout},
                )
                raw_text = response.text.strip()
                break
            except Exception as exc:
                err_str = str(exc)
                if ("429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str) and attempts < max_attempts:
                    import re
                    m_delay = re.search(r'retry in (\d+(?:\.\d+)?)s', err_str, re.IGNORECASE)
                    sleep_sec = float(m_delay.group(1)) + 2.0 if m_delay else 40.0
                    logger.warning("CONTENT_CLASSIFIER rate limit hit page=%d attempt=%d. Sleeping %.1fs...", page.page_number, attempts, sleep_sec)
                    import time
                    time.sleep(sleep_sec)
                else:
                    raise ContentClassifierError(
                        f"page {page.page_number}: content classification failed against {self.model_id}: {exc}"
                    ) from exc

        if not raw_text:
            raise ContentClassifierError(f"page {page.page_number}: empty response from {self.model_id}")

        try:
            parsed = json.loads(raw_text)

            flags = ContentFlags(
                contains_diagram=bool(parsed.get("contains_diagram", False)),
                contains_table=bool(parsed.get("contains_table", False)),
                contains_equation=bool(parsed.get("contains_equation", False)),
                contains_struck_out=bool(parsed.get("contains_struck_out", False)),
                non_latin_script=bool(parsed.get("non_latin_script", False)),
            )

            if self.cache is not None:
                self.cache.put(key, {"flags": asdict(flags), "raw_response": raw_text})

            logger.info("CONTENT_CLASSIFIER completed page=%d flags=%s", page.page_number, flags.flagged_reasons())
            return flags
        except Exception as exc:
            raise ContentClassifierError(
                f"page {page.page_number}: failed to parse classifier JSON output: {exc}"
            ) from exc

    def classify_region(
        self,
        page_images: Sequence[PageImage],
        region: QuestionRegion,
    ) -> ContentFlags:
        """Classify non-text content across the pages belonging to a QuestionRegion."""
        # Find pages matching region.page_numbers
        region_pages = [p for p in page_images if p.page_number in region.page_numbers]
        if not region_pages:
            # Fallback to classifying all provided pages if page matching is empty
            region_pages = list(page_images)

        combined_flags = {
            "contains_diagram": False,
            "contains_table": False,
            "contains_equation": False,
            "contains_struck_out": False,
            "non_latin_script": False,
        }

        for p_img in region_pages:
            flags = self.classify_page(p_img)
            if flags.contains_diagram:
                combined_flags["contains_diagram"] = True
            if flags.contains_table:
                combined_flags["contains_table"] = True
            if flags.contains_equation:
                combined_flags["contains_equation"] = True
            if flags.contains_struck_out:
                combined_flags["contains_struck_out"] = True
            if flags.non_latin_script:
                combined_flags["non_latin_script"] = True

        return ContentFlags(**combined_flags)

    @staticmethod
    def check_transcription_struck_out(region: QuestionRegion) -> ContentFlags:
        """Extract contains_struck_out flag directly from a QuestionRegion's own lines.

        Every content flag is strictly per-question derived from that question's own lines.
        A flag on one line never propagates to sibling questions on the same page.
        """
        has_struck = any(getattr(line, "struck_through", False) for line in region.lines)
        return ContentFlags(contains_struck_out=has_struck)

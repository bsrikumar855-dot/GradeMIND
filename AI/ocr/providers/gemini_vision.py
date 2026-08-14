"""Gemini Vision HTR provider. Reads handwriting. Returns text, never marks.

See AI/ocr/providers/base.py for why that sentence is load-bearing, and
AI/ocr/providers/prompts.py for the prompt that enforces it.

WHAT THIS SENDS OVER THE NETWORK
--------------------------------
A page image of a student's handwriting. That is personal data leaving the
system, and `identity_mask` must have been applied before it gets here --
see AI/ocr/identity_mask.py and docs/THIRD_PARTY_PROCESSING.md. This module
refuses to send an unmasked page when a mask region is configured for the exam.

CONFIDENCE
----------
The Gemini API does not expose per-token logprobs for vision transcription, so
there is no confidence to read off the response. Rather than invent one, the
prompt asks the model for a `legibility` rating per line -- how clearly the
handwriting could be read -- and that is what is reported, labelled as what it
is.

This is a MODEL SELF-REPORT, not a calibrated probability. It has never been
compared against human transcription, so it must not be treated as one. It is
carried so lane assignment has something to threshold on, and every Page built
this way is flagged so a reader cannot mistake it for a measured confidence.
Fabricating a plausible number instead would violate §0 rule 2 outright.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from AI.ocr.providers.base import (
    HTRExtractionError,
    HTRProvider,
    Line,
    Page,
    extraction_sha256,
)
from AI.ocr.providers.cache import (
    ExtractionCache,
    cache_key,
    page_to_record,
    record_to_page,
)
from AI.ocr.providers.prompts import (
    TRANSCRIPTION_PROMPT,
    TRANSCRIPTION_PROMPT_VERSION,
    TRANSCRIPTION_SCHEMA,
)
from AI.ocr.rasterize import PageImage

logger = logging.getLogger("GradeMIND.GeminiVisionHTR")

# EXACT. Never an alias like "gemini-flash-latest": a hosted model that changes
# under a stable name breaks replay silently, and the stored extraction would
# no longer correspond to anything reproducible.
DEFAULT_MODEL_ID = "gemini-2.5-flash"

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 2.0
CIRCUIT_BREAKER_THRESHOLD = 5

# The self-reported legibility is not calibrated against anything.
CONFIDENCE_IS_SELF_REPORTED = (
    "page_confidence is a model self-reported legibility rating, NOT a "
    "calibrated probability. Never compared against human transcription. "
    "Must not route a question to AUTO on its own."
)


class CircuitOpen(HTRExtractionError):
    """Too many consecutive failures; stop calling the API."""


@dataclass
class _Breaker:
    threshold: int = CIRCUIT_BREAKER_THRESHOLD
    failures: int = 0
    open: bool = False

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open = True

    def record_success(self) -> None:
        self.failures = 0
        self.open = False


class GeminiVisionHTRProvider(HTRProvider):
    name = "gemini_vision"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: str = DEFAULT_MODEL_ID,
        cache: Optional[ExtractionCache] = None,
        transport: Optional[Callable[[bytes, str], Any]] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff: float = DEFAULT_BACKOFF_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        offline: bool = False,
    ):
        """`transport` is injected so the failure paths are testable without a key.

        It takes (image_bytes, prompt) and returns the raw response object. In
        production it is None and the real client is built lazily.
        """
        if "latest" in model_id.lower() or model_id.endswith("-exp"):
            raise ValueError(
                f"model_id {model_id!r} is a floating alias. Pin an exact model: "
                "a hosted model that changes under a stable name breaks replay "
                "without changing any recorded version."
            )

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key and not offline:
            from dotenv import load_dotenv
            from pathlib import Path
            env_path = Path(__file__).resolve().parent.parent.parent.parent / "backend" / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
            self.api_key = os.environ.get("GEMINI_API_KEY")

        self.model_id = model_id
        self.cache = cache
        self._transport = transport
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff = backoff
        self._sleep = sleep
        self._breaker = _Breaker()
        self.offline = offline

    # ------------------------------------------------------------------

    def describe(self) -> Dict[str, str]:
        return {
            "provider": self.name,
            "model_id": self.model_id,
            "prompt_version": TRANSCRIPTION_PROMPT_VERSION,
            "confidence_note": CONFIDENCE_IS_SELF_REPORTED,
        }

    # ------------------------------------------------------------------

    def extract(self, page: PageImage, hints: Optional[Dict[str, Any]] = None) -> Page:
        key = cache_key(page.page_sha256, self.model_id, TRANSCRIPTION_PROMPT_VERSION)

        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None:
                logger.info(
                    "HTR_STAGE cache_hit page=%s key=%s model_id=%s", page.page_number, key[:24], self.model_id
                )
                return record_to_page(cached)

        if self.offline:
            logger.error("OFFLINE MODE: Cache miss for page=%s key=%s model_id=%s", page.page_number, key[:24], self.model_id)
            raise HTRExtractionError(
                f"Offline mode enabled: cache miss for page {page.page_number} with model {self.model_id}. Network calls forbidden."
            )

        if self._breaker.open:
            raise CircuitOpen(
                f"circuit breaker open after {self._breaker.failures} consecutive "
                f"failures; refusing to call {self.model_id}. Route to "
                "MANDATORY_HUMAN."
            )

        raw = self._call_with_retries(page)
        parsed = self._parse(raw, page)

        if self.cache is not None:
            self.cache.put(key, page_to_record(parsed, _jsonable(raw)))

        return parsed

    # ------------------------------------------------------------------

    def _call_with_retries(self, page: PageImage) -> Any:
        last: Optional[Exception] = None

        attempt = 1
        while attempt <= self.max_attempts:
            try:
                raw = self._invoke(page.image_bytes)
                self._breaker.record_success()
                return raw
            except Exception as exc:
                last = exc
                err_str = str(exc)
                if "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str:
                    logger.warning(
                        "HTR_STAGE rate_limit_quota_hit page=%s error=%s. Sleeping 30s before retry...",
                        page.page_number, exc,
                    )
                    self._sleep(30.0)
                    # Quota wait doesn't count against max_attempts
                    continue
                else:
                    self._breaker.record_failure()
                    logger.warning(
                        "HTR_STAGE attempt_failed page=%s attempt=%d/%d error=%s",
                        page.page_number, attempt, self.max_attempts, exc,
                    )
                    if attempt < self.max_attempts:
                        self._sleep(self.backoff * (2 ** (attempt - 1)))
                    attempt += 1

        # Exhausted. RAISE. Returning an empty Page here would be the
        # silent-zero defect re-entering through a new provider: downstream,
        # an empty transcription is indistinguishable from a blank page and
        # scores zero under any scheme.
        raise HTRExtractionError(
            f"page {page.page_number}: extraction failed after "
            f"{self.max_attempts} attempts against {self.model_id}: {last}. "
            "Route to MANDATORY_HUMAN. No Page is produced."
        ) from last

    def _invoke(self, image_bytes: bytes) -> Any:
        if self._transport is not None:
            return self._transport(image_bytes, TRANSCRIPTION_PROMPT)

        if not self.api_key:
            raise HTRExtractionError(
                "GEMINI_API_KEY is not set and no transport was injected. "
                "Refusing to proceed: there is no extraction to return."
            )

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_id)
        return model.generate_content(
            [
                {"mime_type": "image/png", "data": image_bytes},
                TRANSCRIPTION_PROMPT,
            ],
            generation_config={
                # Deterministic as far as the API allows. This is best effort,
                # not a guarantee -- hosted inference is not reproducible, which
                # is exactly why the cache is the audit record.
                "temperature": 0.0,
                "top_p": 1.0,
                "candidate_count": 1,
                "response_mime_type": "application/json",
                "response_schema": TRANSCRIPTION_SCHEMA,
            },
            request_options={"timeout": self.timeout},
        )

    # ------------------------------------------------------------------

    def _parse(self, raw: Any, page: PageImage) -> Page:
        """Validate strictly. A malformed response is an error, not a partial Page."""
        text = _response_text(raw)
        if not text:
            raise HTRExtractionError(
                f"page {page.page_number}: response carried no text payload"
            )

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTRExtractionError(
                f"page {page.page_number}: response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, dict) or "lines" not in payload:
            raise HTRExtractionError(
                f"page {page.page_number}: response has no 'lines' key; got "
                f"{sorted(payload) if isinstance(payload, dict) else type(payload).__name__}"
            )

        raw_lines = payload["lines"]
        if not isinstance(raw_lines, list):
            raise HTRExtractionError(
                f"page {page.page_number}: 'lines' is {type(raw_lines).__name__}, expected list"
            )

        lines: List[Line] = []
        warnings: List[str] = []

        for index, item in enumerate(raw_lines):
            if not isinstance(item, dict):
                raise HTRExtractionError(
                    f"page {page.page_number}: line {index} is "
                    f"{type(item).__name__}, expected object"
                )
            if "text" not in item:
                raise HTRExtractionError(
                    f"page {page.page_number}: line {index} has no 'text'"
                )

            legibility = item.get("legibility")
            if legibility is not None:
                try:
                    legibility = float(legibility)
                except (TypeError, ValueError):
                    raise HTRExtractionError(
                        f"page {page.page_number}: line {index} legibility "
                        f"{item.get('legibility')!r} is not a number"
                    ) from None
                if not 0.0 <= legibility <= 1.0:
                    raise HTRExtractionError(
                        f"page {page.page_number}: line {index} legibility "
                        f"{legibility} outside [0, 1]"
                    )

            bbox = _bbox(item.get("bbox"))
            if bbox is None and item.get("bbox") is not None:
                warnings.append(f"line {index + 1}: unusable bbox {item.get('bbox')!r}")

            is_struck = bool(item.get("struck_through", False))
            if is_struck:
                warnings.append(f"line {index + 1}: marked struck through by the candidate")

            lines.append(
                Line(
                    text=str(item["text"]),
                    confidence=legibility,
                    bbox=bbox,
                    script=item.get("script"),
                    struck_through=is_struck,
                )
            )

        # An empty transcription is a legitimate outcome -- a genuinely blank
        # page -- but it must be flagged, never quietly passed on as an answer.
        if not lines:
            warnings.append(
                "no lines transcribed: page is blank or entirely illegible. "
                "BLANK_PAGE/ILLEGIBLE - route to MANDATORY_HUMAN, do not mark."
            )

        confidences = [l.confidence for l in lines if l.confidence is not None]
        page_confidence = min(confidences) if confidences else None
        # min, not mean: one illegible line in an otherwise clean page is the
        # thing that should pull a question out of AUTO. A mean would bury it.

        return Page(
            lines=tuple(lines),
            page_confidence=page_confidence,
            provider=self.name,
            model_id=self.model_id,
            prompt_version=TRANSCRIPTION_PROMPT_VERSION,
            page_number=page.page_number,
            page_sha256=page.page_sha256,
            extraction_sha256=extraction_sha256(lines),
            rasterize_version=page.rasterize_version,
            raw_response_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            warnings=tuple(warnings),
        )


# ---------------------------------------------------------------------------


def _response_text(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    for attr in ("text", "content"):
        value = getattr(raw, attr, None)
        if isinstance(value, str):
            return value
    if isinstance(raw, dict):
        for key in ("text", "content"):
            if isinstance(raw.get(key), str):
                return raw[key]
    return ""


def _bbox(value: Any) -> Optional[Tuple[float, float, float, float]]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    return (x0, y0, x1, y1)


def _jsonable(raw: Any) -> Any:
    if isinstance(raw, (str, int, float, bool, type(None), list, dict)):
        return raw
    return _response_text(raw) or repr(raw)

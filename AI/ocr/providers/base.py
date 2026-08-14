"""The HTR provider contract.

    A provider READS. The deterministic core MARKS.

Everything in this module returns text, confidence, and geometry. Nothing here
returns a mark, a score, a grade, feedback, or any judgement about whether an
answer is correct. That separation is the architectural spine (CLAUDE.md §0
rule 4), and it is not a stylistic preference: a mark has to survive an appeal,
which means reconstructing criterion -> evidence span -> arithmetic. A number a
model produced cannot be reconstructed that way, so rule 3 forbids awarding it.

A provider's output feeds `ValuePointMatcher` -> `ScoreComputer` exactly as
typed text does today. If a provider ever gains a method that returns marks,
the architecture has been broken, not extended.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from AI.ocr.rasterize import PageImage


class HTRExtractionError(RuntimeError):
    """Extraction failed and produced nothing usable.

    Raised instead of returning an empty or low-confidence Page. Returning a
    Page with no lines would be indistinguishable downstream from a genuinely
    blank answer, which is the silent-zero defect closed in
    AI/ocr/ocr_manager.py. It must not re-enter through a provider.

    Callers route this to MANDATORY_HUMAN. They must not catch it and
    substitute empty text.
    """


@dataclass(frozen=True)
class Line:
    """One transcribed line.

    `confidence` is Optional and None means UNKNOWN, not zero and not "fine".
    A provider that cannot honestly report per-line confidence must say so;
    lane assignment treats unknown as un-AUTO-able. Inventing a plausible
    number here would be fabricating a confidence value, which §0 rule 2
    forbids outright.
    """

    text: str
    confidence: Optional[float]
    bbox: Optional[Tuple[float, float, float, float]]  # x0, y0, x1, y1
    script: Optional[str] = None  # "Latin", "Devanagari", "mixed", ...


@dataclass(frozen=True)
class Page:
    """The transcription of one page image. Contains no marks."""

    lines: Tuple[Line, ...]
    page_confidence: Optional[float]
    provider: str
    model_id: str
    prompt_version: str
    page_number: int
    page_sha256: str
    extraction_sha256: str
    rasterize_version: str
    raw_response_sha256: Optional[str] = None
    warnings: Tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    def provenance(self) -> Dict[str, Any]:
        """Everything needed to say which code and which model produced this."""
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "rasterize_version": self.rasterize_version,
            "page_sha256": self.page_sha256,
            "extraction_sha256": self.extraction_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "page_confidence": self.page_confidence,
        }


def extraction_sha256(lines: Sequence[Line]) -> str:
    """Stable hash of a transcription, for replay comparison."""
    payload = json.dumps(
        [
            {"text": l.text, "confidence": l.confidence, "bbox": list(l.bbox) if l.bbox else None}
            for l in lines
        ],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class HTRProvider(ABC):
    """Read a page image. Return text. Never a mark."""

    name: str = "abstract"

    @abstractmethod
    def extract(self, page: PageImage, hints: Optional[Dict[str, Any]] = None) -> Page:
        """Transcribe one page.

        Raises:
            HTRExtractionError: on any failure. Never returns an empty Page to
                signal failure.
        """

    @abstractmethod
    def describe(self) -> Dict[str, str]:
        """Pinned identity of this provider: model id, prompt version, etc."""

"""Value-point marking - the data contract.

Replaces similarity-as-proxy scoring. The distinction that matters:

    An LLM or a matcher finds EVIDENCE. Arithmetic decides the MARK.

Nothing in this module or in `score_computer` calls a model. A model's output
arrives as `MatchResult` - a claim that a specific value point was or was not
supported by a specific span of the answer - and the scorer turns those claims
into a number by rules that are the same on every run, forever.

Why this replaces the old path, with measured numbers rather than a preference:

    'ATP' vs a sentence containing 'ATP' verbatim ....... 0.651  (threshold 0.68)
    correct paraphrase ................................. 0.6239
    wrong but topical .................................. 0.6782

Sentence-embedding cosine ranks topical relatedness. It does not detect
containment, and on that second pair it ranks a wrong answer above a correct
one. No threshold repairs either property, because neither is what the metric
measures. See docs/phases/PHASE_0_REPORT.md §10.

Everything here is frozen and hashable so that a scoring run cannot mutate its
own inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

# Bumped whenever scoring arithmetic changes. Recorded on every QuestionScore:
# a mark is only defensible if you can say which engine produced it.
ENGINE_VERSION = "value-point-engine/0.1.0-demo"


class MatchMode(str, Enum):
    """How a value point is looked for in an answer."""

    EXACT = "EXACT"
    SEMANTIC = "SEMANTIC"
    NUMERIC = "NUMERIC"
    STEP = "STEP"


class GroupRule(str, Enum):
    ALL = "ALL"
    ANY_N = "ANY_N"


@dataclass(frozen=True)
class ValuePoint:
    """One creditable claim in a marking scheme.

    `marks` is what this point is worth on its own. Inside an ANY_N group the
    group allocation caps what the group can contribute regardless.
    """

    id: str
    text: str
    marks: float
    acceptable_variants: Tuple[str, ...] = ()
    match_mode: MatchMode = MatchMode.EXACT

    group_id: Optional[str] = None
    group_rule: Optional[GroupRule] = None
    group_n: Optional[int] = None

    # NUMERIC only.
    expected_value: Optional[float] = None
    tolerance: Optional[float] = None
    unit: Optional[str] = None

    def __post_init__(self) -> None:
        if self.marks < 0:
            raise ValueError(f"{self.id}: marks cannot be negative ({self.marks})")
        if self.group_rule is GroupRule.ANY_N and not self.group_n:
            raise ValueError(f"{self.id}: ANY_N group requires group_n")
        if self.group_id and self.group_rule is None:
            raise ValueError(f"{self.id}: group_id set without group_rule")


@dataclass(frozen=True)
class SchemeQuestion:
    id: str
    question_number: str
    question_text: str
    max_marks: float
    value_points: Tuple[ValuePoint, ...]

    def __post_init__(self) -> None:
        if self.max_marks <= 0:
            raise ValueError(f"{self.id}: max_marks must be positive")
        if not self.value_points:
            raise ValueError(f"{self.id}: a question needs at least one value point")


@dataclass(frozen=True)
class MatchResult:
    """A claim that a value point was, or was not, supported by the answer.

    `evidence_span` is a pair of character offsets into the answer text. It is
    mandatory for a positive match: master spec rule 3 requires every mark to
    trace to a criterion id, a character span, and an engine version, and a
    match with no span cannot satisfy that. Enforced in __post_init__ rather
    than left to a caller's discipline.

    `uncalibrated` propagates to the output and is set by any matcher whose
    threshold has not been derived from a labelled set. There is no labelled
    set, so every SEMANTIC result carries it.
    """

    value_point_id: str
    matched: bool
    evidence_span: Optional[Tuple[int, int]]
    method: str
    score: float
    uncalibrated: bool = False

    def __post_init__(self) -> None:
        if self.matched and self.evidence_span is None:
            raise ValueError(
                f"{self.value_point_id}: matched=True with no evidence_span. "
                "A mark that cannot point at the text that earned it is not "
                "defensible on appeal."
            )
        if self.evidence_span is not None:
            start, end = self.evidence_span
            if start < 0 or end < start:
                raise ValueError(
                    f"{self.value_point_id}: invalid evidence_span {self.evidence_span}"
                )


@dataclass(frozen=True)
class AwardLine:
    """One line of the derivation: what a single value point contributed."""

    value_point_id: str
    text: str
    awarded: float
    possible: float
    matched: bool
    evidence_span: Optional[Tuple[int, int]]
    method: str
    reason: str
    uncalibrated: bool = False


@dataclass(frozen=True)
class QuestionScore:
    total: float
    max_marks: float
    awarded: Tuple[AwardLine, ...]
    not_awarded: Tuple[AwardLine, ...]
    derivation: str
    engine_version: str = ENGINE_VERSION
    uncalibrated: bool = False

    def as_dict(self) -> dict:
        def line(a: AwardLine) -> dict:
            return {
                "value_point_id": a.value_point_id,
                "text": a.text,
                "awarded": a.awarded,
                "possible": a.possible,
                "matched": a.matched,
                "evidence_span": list(a.evidence_span) if a.evidence_span else None,
                "method": a.method,
                "reason": a.reason,
                "uncalibrated": a.uncalibrated,
            }

        return {
            "total": self.total,
            "max_marks": self.max_marks,
            "awarded": [line(a) for a in self.awarded],
            "not_awarded": [line(a) for a in self.not_awarded],
            "derivation": self.derivation,
            "engine_version": self.engine_version,
            "uncalibrated": self.uncalibrated,
            "disclaimer": DISCLAIMER,
        }


DISCLAIMER = "SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS"

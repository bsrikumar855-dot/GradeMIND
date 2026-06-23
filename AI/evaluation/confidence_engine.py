"""
GradeMIND Confidence Engine v2.

Produces a trustworthy, evidence-backed, per-question confidence score by
combining five orthogonal signals:

    1. OCR quality          (source reliability)
    2. Concept coverage     (subject-matter completeness)
    3. Semantic alignment   (token-level meaning overlap)
    4. Explainability       (evidence-backed match quality)
    5. Fairness             (bias-neutrality of the grading context)

Design constraints
------------------
- scorer.py is NOT modified.  The existing ``generate_confidence()`` in
  scorer.py continues to compute the *submission-level* aggregated score.
  This engine owns the *question-level* signal.
- No new concept extraction, matching, or scoring logic is duplicated.
  All inputs come from upstream engines that have already run.
- The legacy ``QuestionEvaluation.confidence`` field is preserved and
  populated with ``overall_confidence`` for full backward compatibility.
"""

import logging
import statistics
from typing import List, Optional

from AI.schemas.evaluation_schema import ConfidenceBreakdown, ExplainabilityResult

logger = logging.getLogger("GradeMIND.ConfidenceEngine")

# ---------------------------------------------------------------------------
# Weights — must sum to 1.0
# ---------------------------------------------------------------------------
_W_CONCEPT    = 0.30   # Concept coverage  — most reliable academic signal
_W_SEMANTIC   = 0.25   # Semantic alignment — token-level meaning overlap
_W_EXPL       = 0.20   # Explainability   — evidence-backed verification
_W_OCR        = 0.15   # OCR confidence   — source quality
_W_FAIRNESS   = 0.10   # Fairness score   — bias-neutrality

_DISCREPANCY_PENALTY = 0.05  # Per discrepancy, max cap at 0.25 total


class ConfidenceEngine:
    """
    Confidence Engine v2.

    Call ``calculate()`` after the Explainability layer and before final
    ``QuestionEvaluation`` construction to obtain a structured
    ``ConfidenceBreakdown``.
    """

    def calculate(
        self,
        ocr_confidence: float,
        concept_coverage: float,
        semantic_alignment: float,
        explainability_result: Optional[ExplainabilityResult],
        fairness_score: float,
        discrepancy_count: int = 0,
    ) -> ConfidenceBreakdown:
        """
        Compute per-question confidence with a transparent per-signal breakdown.

        Parameters
        ----------
        ocr_confidence:
            Aggregate OCR document confidence (0.0–1.0).
        concept_coverage:
            Concept coverage percentage (0.0–100.0) or ratio (0.0–1.0).
            Values > 1.0 are treated as percentages and divided by 100.
        semantic_alignment:
            Semantic similarity score (0.0–1.0) from ``ConceptCoverageEngine``.
        explainability_result:
            ``ExplainabilityResult`` from the Explainability Engine, or
            ``None`` if the engine did not run (graceful degradation).
        fairness_score:
            Bias-neutrality score (0.0–1.0) from ``detect_bias()``.
        discrepancy_count:
            Number of marking discrepancies detected by ``verify_marking()``.

        Returns
        -------
        ConfidenceBreakdown
            Structured breakdown with per-signal scores and ``overall_confidence``.
        """
        try:
            ocr_score        = self._clamp(ocr_confidence)
            concept_score    = self._to_ratio(concept_coverage)
            semantic_score   = self._clamp(semantic_alignment)
            expl_score       = self._explainability_score(explainability_result)
            fairness         = self._clamp(fairness_score)

            # Discrepancy penalty — capped at 5 discrepancies (0.25)
            penalty = min(discrepancy_count * _DISCREPANCY_PENALTY, 0.25)

            overall = (
                (concept_score  * _W_CONCEPT)
                + (semantic_score * _W_SEMANTIC)
                + (expl_score     * _W_EXPL)
                + (ocr_score      * _W_OCR)
                + (fairness       * _W_FAIRNESS)
                - penalty
            )
            overall = self._clamp(overall)

            breakdown = ConfidenceBreakdown(
                overall_confidence=round(overall, 4),
                ocr_confidence=round(ocr_score, 4),
                concept_coverage_score=round(concept_score, 4),
                semantic_alignment_score=round(semantic_score, 4),
                explainability_score=round(expl_score, 4),
                fairness_score=round(fairness, 4),
            )

            logger.info(
                "CONFIDENCE_V2 overall=%.4f ocr=%.4f concept=%.4f semantic=%.4f "
                "expl=%.4f fairness=%.4f discrepancies=%d penalty=%.4f",
                overall, ocr_score, concept_score, semantic_score,
                expl_score, fairness, discrepancy_count, penalty,
            )
            return breakdown

        except Exception:
            logger.exception(
                "ConfidenceEngine encountered an error; returning neutral fallback."
            )
            return self._neutral_breakdown()

    # ------------------------------------------------------------------
    # Explainability sub-score
    # ------------------------------------------------------------------

    def _explainability_score(
        self, result: Optional[ExplainabilityResult]
    ) -> float:
        """
        Derive an evidence-backed explainability sub-score from
        ``ExplainabilityResult``.

        Formula
        -------
        ::

            coverage_score    = coverage_percentage / 100
            evidence_score    = mean(e.confidence for e in evidence) or 1.0
            missing_penalty   = 0.05 × len(missing_reasoning)
            explainability    = coverage_score × evidence_score × (1 − missing_penalty)
            clamped to [0.0, 1.0]

        When no ExplainabilityResult is available (engine not run), a
        neutral score of 0.5 is returned so overall confidence degrades
        gracefully rather than collapsing to zero.
        """
        if result is None:
            return 0.5  # graceful degradation — explainability not computed

        coverage_score = self._to_ratio(result.coverage_percentage)

        if result.evidence:
            evidence_score = statistics.mean(
                max(0.0, min(1.0, e.confidence)) for e in result.evidence
            )
        else:
            # No evidence items: coverage exists but wasn't textually verified
            # → penalise moderately, but don't zero-out entirely
            evidence_score = 0.5

        missing_count   = len(result.missing_reasoning)
        missing_penalty = min(0.05 * missing_count, 0.50)  # cap at 50% penalty

        raw = coverage_score * evidence_score * (1.0 - missing_penalty)
        return self._clamp(raw)

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a float to [0.0, 1.0]."""
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _to_ratio(value: float) -> float:
        """
        Convert a value that might be a percentage (0–100) or a ratio (0–1)
        into a 0–1 ratio.  Anything > 1.0 is assumed to be a percentage.
        """
        if value > 1.0:
            return max(0.0, min(1.0, float(value) / 100.0))
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _neutral_breakdown() -> ConfidenceBreakdown:
        """Return a safe fallback breakdown used when the engine errors."""
        return ConfidenceBreakdown(
            overall_confidence=0.5,
            ocr_confidence=0.5,
            concept_coverage_score=0.5,
            semantic_alignment_score=0.5,
            explainability_score=0.5,
            fairness_score=0.5,
        )

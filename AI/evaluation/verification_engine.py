"""
Verification Engine for the GradeMIND Evaluation Pipeline.

This layer compares the primary deterministic evaluation against the secondary
Gemini evaluation to detect grading anomalies, moderate/major disagreements,
and confidence inconsistencies. It classifies the root cause and flags questions
requiring manual review.

IMPORTANT: This engine NEVER modifies score_awarded, confidence, or marks.
It is strictly an informational safety layer.
"""

import logging
from typing import List, Optional

from AI.schemas.evaluation_schema import VerificationResult, VerificationStatus

logger = logging.getLogger("GradeMIND.VerificationEngine")

class VerificationEngine:
    """
    Acts as a safety reviewer by comparing GradeMIND and Gemini outputs.
    """

    def verify(
        self,
        gm_score: float,
        gemini_score: float,
        gm_confidence: float,
        gemini_confidence: float,
        gm_missing_concepts: List[str],
        gemini_missing_concepts: List[str],
    ) -> VerificationResult:
        """
        Compare the primary and secondary evaluations and return a VerificationResult.
        """
        try:
            score_diff = abs(gm_score - gemini_score)
            conf_diff = abs(gm_confidence - gemini_confidence)

            # 1. Determine Disagreement Rules
            status = VerificationStatus.PASS
            review_required = False

            if score_diff > 2.0:
                status = VerificationStatus.MAJOR_DISAGREEMENT
                review_required = True
            elif score_diff > 0.5:
                status = VerificationStatus.MODERATE_DISAGREEMENT
                review_required = False
            elif conf_diff > 0.30:
                status = VerificationStatus.LOW_CONFIDENCE
                review_required = True
            else:
                status = VerificationStatus.PASS
                review_required = False

            # 2. Determine Root Cause
            root_cause = self._determine_root_cause(
                status=status,
                score_diff=score_diff,
                conf_diff=conf_diff,
                gm_missing=set(c.lower().strip() for c in gm_missing_concepts),
                gemini_missing=set(c.lower().strip() for c in gemini_missing_concepts),
            )

            # 3. Formulate Reason
            reason = self._formulate_reason(status, score_diff, conf_diff, root_cause)

            result = VerificationResult(
                status=status,
                score_difference=round(score_diff, 4),
                confidence_difference=round(conf_diff, 4),
                root_cause=root_cause,
                review_required=review_required,
                reason=reason,
            )

            logger.info(
                f"VERIFICATION_STAGE status={status.value} score_diff={score_diff:.2f} "
                f"root_cause={root_cause} review_required={review_required}"
            )
            return result

        except Exception as e:
            logger.error(f"VerificationEngine encountered an error: {e}")
            # Safe fallback if verification fails
            return VerificationResult(
                status=VerificationStatus.PASS,
                score_difference=0.0,
                confidence_difference=0.0,
                root_cause="UNKNOWN",
                review_required=False,
                reason="Verification failed due to an internal error.",
            )

    def _determine_root_cause(
        self,
        status: VerificationStatus,
        score_diff: float,
        conf_diff: float,
        gm_missing: set,
        gemini_missing: set,
    ) -> str:
        """
        Heuristic to infer the root cause of the disagreement.
        """
        if status == VerificationStatus.PASS:
            return "NONE"

        missing_concept_diff = bool(gm_missing.symmetric_difference(gemini_missing))

        if status == VerificationStatus.LOW_CONFIDENCE:
            return "CONFIDENCE_INCONSISTENCY"

        if status in [VerificationStatus.MODERATE_DISAGREEMENT, VerificationStatus.MAJOR_DISAGREEMENT]:
            if missing_concept_diff:
                # If they disagree on what concepts were missing, it's either a concept mismatch or missing concept detection issue
                return "MISSING_CONCEPT_DIFFERENCE"
            else:
                # If they agree on concepts but disagree on score, it's usually semantic or rubric
                return "SEMANTIC_INTERPRETATION"
                
        return "UNKNOWN"

    def _formulate_reason(
        self, status: VerificationStatus, score_diff: float, conf_diff: float, root_cause: str
    ) -> str:
        """
        Generate a human-readable reason for the UI.
        """
        if status == VerificationStatus.PASS:
            return "Evaluations are aligned."
        if status == VerificationStatus.LOW_CONFIDENCE:
            return f"Confidence gap of {conf_diff:.2f} detected between primary and secondary engines."
        if status == VerificationStatus.MODERATE_DISAGREEMENT:
            return f"Moderate score difference of {score_diff:.2f} marks detected. Likely due to {root_cause}."
        if status == VerificationStatus.MAJOR_DISAGREEMENT:
            return f"Major score difference of {score_diff:.2f} marks detected. Immediate review required."
        return "Unknown anomaly detected."

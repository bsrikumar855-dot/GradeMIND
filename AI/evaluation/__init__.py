"""
GradeMIND Evaluation Package.
Contains rubric engine, scorer, feedback generator, and fairness agent.
"""

from AI.evaluation.rubric_engine import (
    generate_rubric,
    evaluate_keywords,
    evaluate_coverage,
    calculate_partial_credit,
)
from AI.evaluation.scorer import (
    calculate_marks,
    normalize_score,
    aggregate_scores,
    generate_confidence,
)
from AI.evaluation.feedback import (
    generate_strengths,
    generate_weaknesses,
    generate_improvements,
    generate_summary,
    compile_feedback,
)
from AI.evaluation.fairness import (
    validate_score_consistency,
    detect_outliers,
    detect_bias,
    verify_marking,
)

__all__ = [
    "generate_rubric",
    "evaluate_keywords",
    "evaluate_coverage",
    "calculate_partial_credit",
    "calculate_marks",
    "normalize_score",
    "aggregate_scores",
    "generate_confidence",
    "generate_strengths",
    "generate_weaknesses",
    "generate_improvements",
    "generate_summary",
    "compile_feedback",
    "validate_score_consistency",
    "detect_outliers",
    "detect_bias",
    "verify_marking",
]

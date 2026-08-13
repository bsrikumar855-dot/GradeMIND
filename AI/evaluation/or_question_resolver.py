"""
GradeMIND OR-Question Resolver.

Detects alternative questions (OR / Either / Any One / Attempt Any One)
in question paper text, groups them into QuestionGroup structures, and
during evaluation selects the best-matching alternative to score.

This module is the authoritative source for OR-question handling.
It is used by:
  - submission_service._parse_question_context  (question parsing)
  - ai_service.evaluate_autonomously            (answer matching + evaluation)
  - ai_service.evaluate_with_answer_key         (answer matching + evaluation)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("GradeMIND.ORQuestionResolver")

# ─────────────────────────────────────────────────────────────────────────────
# Patterns that signal OR-group boundaries in question text
# ─────────────────────────────────────────────────────────────────────────────

#: Patterns that indicate an OR separator between two question alternatives.
OR_SEPARATOR_PATTERNS: List[re.Pattern] = [
    # Standalone "OR" on its own line (most common in Indian board exams)
    re.compile(r"(?:^|\n)\s*OR\s*(?:\n|$)", re.IGNORECASE),
    # "Either ... or ..." style
    re.compile(r"\bEither\b.{5,200}\bor\b", re.IGNORECASE | re.DOTALL),
    # "Attempt Any One" / "Any One of the following" on a line by itself
    re.compile(r"(?:^|\n)\s*(?:Attempt\s+)?Any[\s-]One(?:\s+of\s+the\s+following)?[\s:]*(?:\n|$)", re.IGNORECASE),
]

#: Simple OR regex used for inline detection within a single-line string.
INLINE_OR_RE = re.compile(
    r"\s+(?:OR|Either|Any[\s-]?One)\s+",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QuestionAlternative:
    """One choice in an OR-type group."""
    label: str                 # e.g. "question_1_optA"
    text: str                  # Full alternative question text
    marks: Optional[float] = None


@dataclass
class QuestionGroup:
    """
    Represents a set of alternative questions where the student must
    answer exactly one.  type is always "OR".
    """
    group_id: str              # e.g. "question_1"
    group_type: str            # always "OR"
    alternatives: List[QuestionAlternative] = field(default_factory=list)
    marks: Optional[float] = None  # Marks available (same for all alternatives)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "group_type": self.group_type,
            "marks": self.marks,
            "alternatives": [
                {"label": a.label, "text": a.text, "marks": a.marks}
                for a in self.alternatives
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Core detection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_marks(text: str) -> Optional[float]:
    """Extract mark value from patterns like [5 Marks] or (5m)."""
    match = re.search(
        r"[\[\(]\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*[\]\)]",
        text,
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def has_or_structure(text: str) -> bool:
    """
    Return True when the given text contains an OR-type separator.

    Checks multi-line patterns first (more precise), then inline pattern.

    Args:
        text: Raw question text (may be multi-line or normalised).

    Returns:
        True if OR structure is detected.
    """
    for pat in OR_SEPARATOR_PATTERNS:
        if pat.search(text):
            return True
    if INLINE_OR_RE.search(text):
        return True
    return False


def split_or_alternatives(text: str) -> List[str]:
    """
    Split a question text into its OR-separated alternatives.

    Handles:
      - Multi-line "\\nOR\\n" separators
      - Inline " OR " within a single line
      - "Any One" / "Attempt Any One" separators

    Args:
        text: Question text that has been confirmed to contain an OR structure.

    Returns:
        List of alternative question texts (stripped).  Always ≥ 2 elements.
    """
    # Try the most specific patterns first (multi-line standalone OR)
    standalone_or = re.compile(
        r"\n\s*(?:OR|Either|Any[\s-]?One(?:\s+of\s+the\s+following)?)\s*\n",
        re.IGNORECASE,
    )
    parts = standalone_or.split(text)
    if len(parts) >= 2:
        return [p.strip() for p in parts if p.strip()]

    # Fallback: inline OR
    parts = re.split(r"\s+OR\s+", text, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return [p.strip() for p in parts if p.strip()]

    # Fallback: Either/Any One inline
    parts = re.split(r"\s+(?:Either|Any[\s-]?One)\s+", text, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return [p.strip() for p in parts if p.strip()]

    # Should not reach here if has_or_structure() returned True,
    # but return original text as single alternative to be safe.
    logger.warning("split_or_alternatives: could not split text: %r", text[:120])
    return [text.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Question paper parser integration
# ─────────────────────────────────────────────────────────────────────────────

def parse_questions_with_or(
    question_text: str,
    total_marks: float,
) -> Dict[str, Any]:
    """
    Parse a question paper text into a question map that correctly handles
    OR-type alternatives.

    This is a drop-in replacement for the naive regex parser in
    submission_service._parse_question_context.

    For regular questions, returns:
        { "question_1": {"text": "...", "marks": N, "or_group": None} }

    For OR questions, returns:
        {
          "question_1": {
              "text": "Explain stream-lined flow OR Explain Kolmogorov turbulence",
              "marks": N,
              "or_group": QuestionGroup(...),
          }
        }

    Args:
        question_text: Full text of the question paper.
        total_marks:   Total exam marks (used to distribute if marks unspecified).

    Returns:
        Dict of question_id → question info dict.

    Raises:
        ValueError: If question_text is empty.
    """
    text = re.sub(r"\s+", " ", (question_text or "").strip())
    if not text:
        raise ValueError("Question text is required for evaluation.")

    # Identify question boundaries (numbered questions)
    q_boundary_re = re.compile(
        r"\b(?:Q|Question)\s*\.?\s*(\d+)\b|(?:^|\s)(\d+)[\.\\)]\s+",
        re.IGNORECASE,
    )
    matches = list(q_boundary_re.finditer(text))

    # Build raw question map first
    raw_questions: Dict[str, str] = {}
    if not matches:
        raw_questions["question_1"] = text
    else:
        for idx, match in enumerate(matches):
            q_num = match.group(1) or match.group(2) or str(idx + 1)
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            q_text = text[start:end].strip()
            if q_text:
                raw_questions[f"question_{q_num}"] = q_text

    # Distribute marks
    questions: Dict[str, Any] = {}
    unresolved: List[str] = []
    for q_id, q_text in raw_questions.items():
        marks = _extract_marks(q_text)
        entry: Dict[str, Any] = {"text": q_text, "marks": marks, "or_group": None}
        if marks is None:
            unresolved.append(q_id)
        questions[q_id] = entry

    if unresolved:
        per_q = round(total_marks / len(raw_questions), 2)
        for q_id in unresolved:
            questions[q_id]["marks"] = per_q

    # Now detect OR structure and attach QuestionGroup
    for q_id, entry in questions.items():
        q_text = entry["text"]

        # Re-check with original (non-normalised) text for multiline OR
        # NOTE: We also try with a reconstructed multiline version
        reconstructed = re.sub(r" OR ", "\nOR\n", q_text, flags=re.IGNORECASE)
        if not has_or_structure(q_text) and not has_or_structure(reconstructed):
            continue  # Not an OR question

        # Prefer reconstructed for splitting if it has multiline OR
        split_source = reconstructed if "\nOR\n" in reconstructed.upper() else q_text
        alternatives_text = split_or_alternatives(split_source)

        if len(alternatives_text) < 2:
            continue  # Could not split — leave as regular question

        marks_per_alt = entry["marks"]
        group = QuestionGroup(
            group_id=q_id,
            group_type="OR",
            marks=marks_per_alt,
        )
        for i, alt_text in enumerate(alternatives_text):
            label_suffix = chr(ord("A") + i)   # A, B, C …
            group.alternatives.append(QuestionAlternative(
                label=f"{q_id}_opt{label_suffix}",
                text=alt_text,
                marks=marks_per_alt,
            ))

        entry["or_group"] = group
        logger.info(
            "OR_RESOLVER detected OR-group question_id=%s alternatives=%d",
            q_id,
            len(group.alternatives),
        )

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# Answer-to-alternative matching
# ─────────────────────────────────────────────────────────────────────────────

def _keyword_overlap(text_a: str, text_b: str) -> float:
    """
    Simple keyword overlap ratio between two strings.
    Used to choose which OR alternative a student answer matches.
    """
    a_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text_a.lower()))
    b_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text_b.lower()))
    if not a_words or not b_words:
        return 0.0
    intersection = a_words & b_words
    return len(intersection) / min(len(a_words), len(b_words))


def select_best_alternative(
    group: QuestionGroup,
    student_answer: str,
) -> Tuple[QuestionAlternative, float, List[Tuple[QuestionAlternative, float]]]:
    """
    Determine which OR alternative the student answered.

    Scores each alternative by keyword overlap with the student answer
    and returns the best-matching one.

    Args:
        group:          QuestionGroup with 2+ alternatives.
        student_answer: OCR-extracted student answer text.

    Returns:
        Tuple of:
          - best_alternative (QuestionAlternative)
          - best_score       (float, 0.0–1.0)
          - all_scores       (list of (alternative, score) pairs, descending)
    """
    scores: List[Tuple[QuestionAlternative, float]] = []
    for alt in group.alternatives:
        score = _keyword_overlap(alt.text, student_answer)
        scores.append((alt, score))
        logger.debug(
            "OR_RESOLVER match_score group=%s alt=%s score=%.3f",
            group.group_id,
            alt.label,
            score,
        )

    scores.sort(key=lambda x: x[1], reverse=True)
    best_alt, best_score = scores[0]

    logger.info(
        "OR_RESOLVER selected group=%s chosen_alt=%s chosen_score=%.3f student_answer_len=%d",
        group.group_id,
        best_alt.label,
        best_score,
        len(student_answer),
    )
    return best_alt, best_score, scores


def resolve_or_question(
    q_id: str,
    question_info: Dict[str, Any],
    student_answer: str,
) -> Tuple[str, str, float]:
    """
    High-level helper: given a question entry and the student answer,
    resolve which alternative was chosen (if OR question), and return
    the resolved question text, the chosen label, and the match score.

    For regular (non-OR) questions, returns original text with score 1.0.

    Args:
        q_id:           Question ID (e.g. "question_1").
        question_info:  Dict with keys "text", "marks", "or_group".
        student_answer: Student answer text.

    Returns:
        (resolved_q_text, chosen_label, match_score)
    """
    group: Optional[QuestionGroup] = question_info.get("or_group")
    if not group:
        # Regular question — no OR selection needed
        return question_info["text"], q_id, 1.0

    best_alt, score, all_scores = select_best_alternative(group, student_answer)
    logger.info(
        "OR_RESOLVER resolved q_id=%s -> alternative=%s (score=%.3f) "
        "| all_scores=%s",
        q_id,
        best_alt.label,
        score,
        [(a.label, round(s, 3)) for a, s in all_scores],
    )
    return best_alt.text, best_alt.label, score

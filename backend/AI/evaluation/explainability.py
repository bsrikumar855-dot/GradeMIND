"""
GradeMIND Explainability Engine.

Builds structured evidence, reasoning statements, and coverage metrics
from *already-computed* evaluation outputs. This module never duplicates
concept extraction, matching, or scoring logic — it consumes the results
produced by ConceptCoverageEngine, the rubric engine, and the scorer.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from AI.evaluation.concept_engine import ConceptCoverageEngine, SYNONYMS
from AI.schemas.evaluation_schema import (
    EvidenceItem,
    ExplainabilityResult,
    RubricCriterion,
)

logger = logging.getLogger("GradeMIND.Explainability")

# ---------------------------------------------------------------------------
# Context-window settings for snippet extraction
# ---------------------------------------------------------------------------
_CONTEXT_WORDS_BEFORE = 1
_CONTEXT_WORDS_AFTER = 2
_MIN_SNIPPET_LENGTH = 3


class ExplainabilityEngine:
    """
    Post-evaluation explainability layer.

    Responsibilities
    ----------------
    1. Build evidence for matched concepts (with supporting answer snippets).
    2. Build evidence for matched rubric criteria.
    3. Generate positive reasoning statements.
    4. Generate missing-concept reasoning statements.
    5. Calculate concept coverage percentage.
    """

    def __init__(self) -> None:
        self._concept_engine = ConceptCoverageEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def explain(
        self,
        student_answer: str,
        rubric_points: List[RubricCriterion],
        matched_concepts: List[str],
        missing_concepts: List[str],
        confidence: float,
    ) -> ExplainabilityResult:
        """
        Build an ``ExplainabilityResult`` from already-computed evaluation data.

        Parameters
        ----------
        student_answer:
            The (possibly sanitised) student answer text.
        rubric_points:
            List of ``RubricCriterion`` objects produced by scoring.
        matched_concepts:
            Concepts the student covered (from ConceptCoverageEngine).
        missing_concepts:
            Concepts the student omitted (from ConceptCoverageEngine).
        confidence:
            Grading confidence score (0.0–1.0) for this question.

        Returns
        -------
        ExplainabilityResult
        """
        try:
            answer_lower = (student_answer or "").lower()

            # 1. Evidence from matched concepts
            concept_evidence = self._extract_evidence_for_concepts(
                answer_lower, matched_concepts, confidence
            )

            # 2. Evidence from matched rubric criteria
            rubric_evidence = self._extract_evidence_for_rubric(
                answer_lower, rubric_points, confidence
            )

            # Merge — concepts first, then rubric (deduplicate by concept key)
            seen_concepts: Set[str] = set()
            evidence: List[EvidenceItem] = []
            for item in concept_evidence + rubric_evidence:
                key = item.concept.lower()
                if key not in seen_concepts:
                    seen_concepts.add(key)
                    evidence.append(item)

            # 3. Positive reasoning
            reasoning = self._generate_reasoning(matched_concepts, rubric_points)

            # 4. Missing-concept reasoning
            missing_reasoning = self._generate_missing_reasoning(missing_concepts)

            # 5. Coverage percentage
            total_concepts = len(matched_concepts) + len(missing_concepts)
            coverage_percentage = (
                round((len(matched_concepts) / total_concepts) * 100.0, 2)
                if total_concepts > 0
                else 0.0
            )

            result = ExplainabilityResult(
                coverage_percentage=coverage_percentage,
                evidence=evidence,
                reasoning=reasoning,
                missing_reasoning=missing_reasoning,
            )

            logger.info(
                "EXPLAINABILITY built coverage=%.1f%% evidence=%d reasoning=%d missing=%d",
                coverage_percentage,
                len(evidence),
                len(reasoning),
                len(missing_reasoning),
            )
            return result

        except Exception:
            logger.exception("Explainability engine encountered an error; returning empty result.")
            return ExplainabilityResult(
                coverage_percentage=0.0,
                evidence=[],
                reasoning=[],
                missing_reasoning=[],
            )

    # ------------------------------------------------------------------
    # Evidence extraction — concepts
    # ------------------------------------------------------------------

    def _extract_evidence_for_concepts(
        self,
        answer_lower: str,
        matched_concepts: List[str],
        base_confidence: float,
    ) -> List[EvidenceItem]:
        """Extract a supporting snippet for every matched concept."""
        evidence: List[EvidenceItem] = []
        if not answer_lower.strip():
            return evidence

        answer_tokens = answer_lower.split()

        for concept in matched_concepts:
            concept_lower = self._concept_engine.normalize_concept(concept)
            if not concept_lower:
                continue

            snippet, match_confidence = self._find_snippet(
                concept_lower, answer_lower, answer_tokens, base_confidence
            )
            if snippet:
                evidence.append(
                    EvidenceItem(
                        concept=concept_lower,
                        matched_text=snippet,
                        confidence=round(match_confidence, 2),
                    )
                )

        return evidence

    # ------------------------------------------------------------------
    # Evidence extraction — rubric criteria
    # ------------------------------------------------------------------

    def _extract_evidence_for_rubric(
        self,
        answer_lower: str,
        rubric_points: List[RubricCriterion],
        base_confidence: float,
    ) -> List[EvidenceItem]:
        """Extract evidence for rubric criteria that were met."""
        evidence: List[EvidenceItem] = []
        if not answer_lower.strip():
            return evidence

        answer_tokens = answer_lower.split()

        for criterion in rubric_points:
            if not criterion.met:
                continue

            # Extract meaningful keywords (length >= 5) from the criterion description
            desc_lower = criterion.description.lower()
            key_terms = re.findall(r"\b[a-zA-Z]{5,}\b", desc_lower)
            common_filter = {
                "should", "would", "could", "about", "using", "where",
                "which", "their", "there", "these", "those", "being",
                "coverage", "expected", "concept",
            }
            key_terms = [t for t in key_terms if t not in common_filter]

            # Use the first matching keyword as the concept label
            for term in key_terms:
                snippet, conf = self._find_snippet(
                    term, answer_lower, answer_tokens, base_confidence
                )
                if snippet:
                    evidence.append(
                        EvidenceItem(
                            concept=term,
                            matched_text=snippet,
                            confidence=round(conf, 2),
                        )
                    )
                    break  # one evidence item per criterion

        return evidence

    # ------------------------------------------------------------------
    # Snippet finder (shared by concept + rubric extractors)
    # ------------------------------------------------------------------

    def _find_snippet(
        self,
        term: str,
        answer_lower: str,
        answer_tokens: List[str],
        base_confidence: float,
    ) -> Tuple[str, float]:
        """
        Locate *term* (or a synonym / fuzzy match) inside the answer and
        return a short context-window snippet plus a confidence score.

        Returns ("", 0.0) when no match is found.
        """
        # --- 1. Direct substring match (multi-word concepts like "carbon dioxide") ---
        if " " in term and term in answer_lower:
            return self._context_around_substring(answer_lower, term), base_confidence

        # --- 2. Exact single-token match ---
        for idx, token in enumerate(answer_tokens):
            clean = re.sub(r"[^a-z0-9]", "", token)
            if clean == term:
                snippet = self._context_around_index(answer_tokens, idx)
                return snippet, base_confidence

        # --- 3. Synonym match (reuse SYNONYMS from concept_engine) ---
        for synonym in SYNONYMS.get(term, set()):
            if synonym in answer_lower:
                return self._context_around_substring(answer_lower, synonym), round(base_confidence * 0.95, 2)

        # --- 4. Fuzzy match (SequenceMatcher ratio >= 0.88, same threshold as concept_engine) ---
        for idx, token in enumerate(answer_tokens):
            clean = re.sub(r"[^a-z0-9]", "", token)
            if len(clean) >= _MIN_SNIPPET_LENGTH and SequenceMatcher(None, term, clean).ratio() >= 0.88:
                snippet = self._context_around_index(answer_tokens, idx)
                ratio = SequenceMatcher(None, term, clean).ratio()
                return snippet, round(ratio, 2)

        return "", 0.0

    # ------------------------------------------------------------------
    # Context-window helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _context_around_index(tokens: List[str], idx: int) -> str:
        """Return a short context window around the token at *idx*."""
        start = max(0, idx - _CONTEXT_WORDS_BEFORE)
        end = min(len(tokens), idx + _CONTEXT_WORDS_AFTER + 1)
        return " ".join(tokens[start:end]).strip()

    @staticmethod
    def _context_around_substring(text: str, substring: str) -> str:
        """Return a context window around the first occurrence of *substring*."""
        pos = text.find(substring)
        if pos == -1:
            return substring

        # Walk backwards to find the start of a context word
        ctx_start = pos
        words_back = 0
        while ctx_start > 0 and words_back < _CONTEXT_WORDS_BEFORE:
            ctx_start -= 1
            if text[ctx_start] == " ":
                words_back += 1
        if ctx_start > 0:
            ctx_start += 1  # skip the space itself

        # Walk forward past the substring to capture trailing context
        ctx_end = pos + len(substring)
        words_forward = 0
        while ctx_end < len(text) and words_forward < _CONTEXT_WORDS_AFTER:
            if text[ctx_end] == " ":
                words_forward += 1
            ctx_end += 1

        return text[ctx_start:ctx_end].strip()

    # ------------------------------------------------------------------
    # Reasoning generators
    # ------------------------------------------------------------------

    def _generate_reasoning(
        self,
        matched_concepts: List[str],
        rubric_points: List[RubricCriterion],
    ) -> List[str]:
        """Produce positive reasoning statements for matched concepts and criteria."""
        reasoning: List[str] = []

        for concept in matched_concepts:
            title = " ".join(w.capitalize() for w in concept.split())
            reasoning.append(
                f"Student correctly identified {concept} as a key factor."
            )

        # Add reasoning from rubric criteria that were met
        for criterion in rubric_points:
            if criterion.met:
                desc = criterion.description.strip()
                # Strip the autonomous evaluator prefix if present
                desc = re.sub(
                    r"^Coverage of expected concept:\s*", "", desc, flags=re.IGNORECASE
                )
                if desc and desc.lower() not in {c.lower() for c in matched_concepts}:
                    reasoning.append(f"Student explained {desc.lower()} involvement.")

        # Deduplicate while preserving order
        seen: Set[str] = set()
        unique: List[str] = []
        for r in reasoning:
            key = r.lower()
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique

    def _generate_missing_reasoning(
        self,
        missing_concepts: List[str],
    ) -> List[str]:
        """Produce negative reasoning statements for missing concepts."""
        reasoning: List[str] = []
        for concept in missing_concepts:
            title = " ".join(w.capitalize() for w in concept.split())
            reasoning.append(f"{title} was not discussed.")
        return reasoning

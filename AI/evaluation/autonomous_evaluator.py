"""
Autonomous evaluator for answer-key-optional grading.

This module does not fabricate scores. It derives marks from question text,
student answer content, concept coverage, answer depth, and explicit fairness
guards. If the question context is missing, it fails loudly.
"""

import re
from typing import Any, Dict, List

from AI.evaluation.concept_engine import ConceptCoverageEngine
from AI.schemas.evaluation_schema import QuestionEvaluation, RubricCriterion


class AutonomousEvaluator:
    """Local deterministic autonomous evaluator."""

    def __init__(self) -> None:
        self.concept_engine = ConceptCoverageEngine()

    def analyze_question(self, question: str, marks: float, subject: str = "") -> Dict[str, Any]:
        if not question or not question.strip():
            raise ValueError("Question text is required for autonomous evaluation.")

        q_lower = question.lower()
        if any(word in q_lower for word in ["compare", "contrast", "distinguish", "difference"]):
            q_type = "COMPARATIVE"
        elif any(word in q_lower for word in ["solve", "calculate", "find", "evaluate"]):
            q_type = "NUMERICAL"
        elif any(word in q_lower for word in ["define", "what is", "state"]):
            q_type = "SHORT_ANSWER"
        elif any(word in q_lower for word in ["list", "name", "mention"]):
            q_type = "LIST"
        else:
            q_type = "DESCRIPTIVE"

        if marks <= 2:
            difficulty = "EASY"
            expected_depth = "brief"
        elif marks <= 5:
            difficulty = "MEDIUM"
            expected_depth = "conceptual"
        else:
            difficulty = "HARD"
            expected_depth = "detailed"

        expected_concepts = self.generate_expected_concepts(question, subject)
        return {
            "question_type": q_type,
            "difficulty": difficulty,
            "expected_depth": expected_depth,
            "expected_concepts": expected_concepts,
            "mark_distribution": self._mark_distribution(expected_concepts, marks),
        }

    def generate_expected_concepts(self, question: str, subject: str = "") -> List[str]:
        return self.concept_engine.filter_concepts(
            self.concept_engine.generate_expected_concepts(question, subject)
        )

    def evaluate_answer(
        self,
        question: str,
        student_answer: str,
        max_marks: float,
        question_number: str = "1",
        subject: str = "",
    ) -> QuestionEvaluation:
        if max_marks <= 0:
            raise ValueError("Maximum marks must be greater than zero for autonomous evaluation.")
        if not question or not question.strip():
            raise ValueError("Question text is required for autonomous evaluation.")

        sanitized_answer = self.concept_engine.sanitize_for_fairness(student_answer or "")
        analysis = self.analyze_question(question, max_marks, subject)

        if not sanitized_answer:
            expected_concepts = self.concept_engine.filter_concepts(analysis["expected_concepts"])
            rubric_points = self._rubric_points(expected_concepts, [], max_marks)
            return QuestionEvaluation(
                question_number=question_number,
                max_marks=max_marks,
                score_awarded=0.0,
                student_answer_extracted="",
                criteria_feedback="No answer content was available for evaluation.",
                matched_keywords=[],
                rubric_points=rubric_points,
                confidence=0.95,
                concept_coverage=0.0,
                missing_concepts=expected_concepts,
                evaluation_mode="AI_AUTONOMOUS",
                difficulty=analysis["difficulty"],
                expected_depth=analysis["expected_depth"],
            )

        coverage = self.concept_engine.evaluate_coverage(question, sanitized_answer, subject)
        semantic_confidence = self.concept_engine.semantic_similarity(question, sanitized_answer, subject)
        concept_coverage_ratio = float(coverage["coverage_percentage"]) / 100.0
        rubric_alignment = self._depth_alignment(sanitized_answer, analysis["expected_depth"])
        factual_penalty = self._factual_error_penalty(sanitized_answer)

        score_ratio = (
            (concept_coverage_ratio * 0.60)
            + (semantic_confidence * 0.25)
            + (rubric_alignment * 0.15)
            - factual_penalty
        )
        score_ratio = min(max(score_ratio, 0.0), 1.0)
        marks_awarded = round(max_marks * score_ratio * 2) / 2
        marks_awarded = round(min(max(marks_awarded, 0.0), max_marks), 2)

        confidence = self.calculate_confidence(
            semantic_confidence=semantic_confidence,
            concept_coverage=concept_coverage_ratio,
            rubric_alignment=rubric_alignment,
        )
        found = self.concept_engine.filter_concepts(list(coverage["concepts_found"]))
        missing = self.concept_engine.filter_concepts(list(coverage["concepts_missing"]))
        expected_concepts = self.concept_engine.filter_concepts(analysis["expected_concepts"])
        rubric_points = self._rubric_points(expected_concepts, found, max_marks)
        feedback = self.generate_feedback(found, missing, marks_awarded, max_marks)

        return QuestionEvaluation(
            question_number=question_number,
            max_marks=max_marks,
            score_awarded=marks_awarded,
            student_answer_extracted=sanitized_answer,
            criteria_feedback=feedback["criteria_feedback"],
            matched_keywords=found,
            rubric_points=rubric_points,
            confidence=confidence,
            concept_coverage=float(coverage["coverage_percentage"]),
            missing_concepts=missing,
            evaluation_mode="AI_AUTONOMOUS",
            difficulty=analysis["difficulty"],
            expected_depth=analysis["expected_depth"],
        )

    def calculate_marks(self, question_evaluations: List[QuestionEvaluation]) -> float:
        return round(sum(q.score_awarded for q in question_evaluations), 2)

    def calculate_confidence(
        self,
        semantic_confidence: float,
        concept_coverage: float,
        rubric_alignment: float,
    ) -> float:
        return round((semantic_confidence + concept_coverage + rubric_alignment) / 3.0, 2)

    def generate_feedback(
        self,
        found_concepts: List[str],
        missing_concepts: List[str],
        marks_awarded: float,
        max_marks: float,
    ) -> Dict[str, Any]:
        ratio = marks_awarded / max_marks if max_marks else 0.0
        strengths = []
        weaknesses = []
        improvements = []
        found_concepts = self.concept_engine.filter_concepts(found_concepts)
        missing_concepts = self.concept_engine.filter_concepts(missing_concepts)

        if found_concepts:
            strengths.append(f"You explained {', '.join(found_concepts[:3])} clearly in relation to the question.")
        if ratio >= 0.75:
            strengths.append("The answer shows strong conceptual understanding.")
        elif ratio >= 0.4:
            strengths.append("The answer shows partial understanding of the question.")

        if missing_concepts:
            weaknesses.append(f"The answer needs clearer explanation of {', '.join(missing_concepts[:3])}.")
            improvements.extend([self._concept_instruction(concept) for concept in missing_concepts[:3]])
        if ratio < 0.5:
            improvements.append("Add clearer explanations and connect ideas directly to the question.")

        if not strengths:
            strengths.append("The response attempts to address the question.")
        if not weaknesses:
            weaknesses.append("No major missing concept was detected.")
        if not improvements:
            improvements.append("Continue adding precise terminology and complete reasoning.")

        return {
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "improvements": improvements[:3],
            "study_recommendations": [
                self._study_topic(concept) for concept in (missing_concepts[:4] or found_concepts[:4])
            ] or ["Core Concepts From This Question"],
            "criteria_feedback": (
                f"Autonomous evaluation found {len(found_concepts)} covered concept(s) "
                f"and {len(missing_concepts)} missing concept(s)."
            ),
        }

    def _concept_instruction(self, concept: str) -> str:
        title = " ".join(word.capitalize() for word in concept.split())
        if concept == "chlorophyll":
            return "Explain how chlorophyll captures sunlight during photosynthesis."
        if concept == "carbon dioxide":
            return "Describe how carbon dioxide is used to form glucose during photosynthesis."
        if concept == "sunlight":
            return "Show how sunlight provides the energy needed for the process."
        return f"Explain the role of {title} in the answer, not just the term."

    def _study_topic(self, concept: str) -> str:
        mapping = {
            "photosynthesis": "Photosynthesis Process",
            "chlorophyll": "Role of Chlorophyll",
            "sunlight": "Light Energy In Photosynthesis",
            "carbon dioxide": "Carbon Dioxide Utilization",
            "water": "Reactants In Photosynthesis",
            "glucose": "Glucose Formation",
            "oxygen": "Oxygen Release",
        }
        return mapping.get(concept, " ".join(word.capitalize() for word in concept.split()))

    def _mark_distribution(self, concepts: List[str], marks: float) -> Dict[str, float]:
        concepts = self.concept_engine.filter_concepts(concepts)
        if not concepts:
            return {}
        per_concept = round(marks / len(concepts), 2)
        distribution = {concept: per_concept for concept in concepts}
        remainder = round(marks - sum(distribution.values()), 2)
        if remainder and concepts:
            distribution[concepts[-1]] = round(distribution[concepts[-1]] + remainder, 2)
        return distribution

    def _rubric_points(
        self,
        expected_concepts: List[str],
        found_concepts: List[str],
        max_marks: float,
    ) -> List[RubricCriterion]:
        expected_concepts = self.concept_engine.filter_concepts(expected_concepts)
        found_concepts = self.concept_engine.filter_concepts(found_concepts)
        distribution = self._mark_distribution(expected_concepts, max_marks)
        found = set(found_concepts)
        points = []
        for idx, concept in enumerate(expected_concepts, 1):
            allocated = distribution.get(concept, 0.0)
            met = concept in found
            points.append(
                RubricCriterion(
                    criterion_id=f"auto_concept_{idx}",
                    description=f"Coverage of expected concept: {concept}",
                    allocated_marks=allocated,
                    marks_awarded=allocated if met else 0.0,
                    met=met,
                )
            )
        return points

    def _depth_alignment(self, answer: str, expected_depth: str) -> float:
        word_count = len(re.findall(r"\b\w+\b", answer))
        thresholds = {"brief": 8, "conceptual": 25, "detailed": 60}
        threshold = thresholds.get(expected_depth, 25)
        return round(min(1.0, word_count / threshold), 2)

    def _factual_error_penalty(self, answer: str) -> float:
        lowered = answer.lower()
        contradiction_terms = ["not", "never", "opposite", "incorrect", "untrue"]
        return 0.15 if sum(1 for term in contradiction_terms if term in lowered) >= 2 else 0.0

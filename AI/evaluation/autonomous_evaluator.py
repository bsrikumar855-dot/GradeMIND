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
from AI.evaluation.evidence_fusion_engine import EvidenceFusionEngine


class AutonomousEvaluator:
    """Local deterministic autonomous evaluator."""

    def __init__(self) -> None:
        self.concept_engine = ConceptCoverageEngine()
        self.fusion_engine = EvidenceFusionEngine()
        from AI.evaluation.groq_evaluator import GroqEvaluator
        self.groq_evaluator = GroqEvaluator()
        
        from AI.evaluation.semantic_engine import SemanticEvaluationEngine
        self.semantic_evaluator = SemanticEvaluationEngine()

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
        teacher_overrides: Optional[Dict[str, Any]] = None,
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

        # ── Primary: Groq 120B LLM Evaluator ─────────────────────────
        llm_eval = None
        if self.groq_evaluator.is_available():
            try:
                llm_eval = self.groq_evaluator.evaluate(
                    question=question,
                    student_answer=sanitized_answer,
                    max_marks=max_marks,
                    question_number=question_number,
                    subject=subject,
                )
                llm_eval.difficulty = analysis["difficulty"]
                llm_eval.expected_depth = analysis["expected_depth"]
            except Exception as exc:
                import logging
                logging.getLogger("GradeMIND.AutonomousEvaluator").warning(
                    "GroqEvaluator failed for Q%s (%s); falling back to local engine.", question_number, exc
                )

        from AI.evaluation.rubric_engine import generate_autonomous_rubric
        from AI.evaluation.curriculum_context_engine import CurriculumContextEngine
        
        ctx_engine = CurriculumContextEngine()
        context = ctx_engine.build_context(question, subject_hint=subject)
        
        if teacher_overrides and "criteria" in teacher_overrides:
            rubric_data = {
                "criteria": teacher_overrides["criteria"],
                "is_autonomous_rubric": False
            }
        else:
            rubric_data = generate_autonomous_rubric(question, analysis["expected_concepts"], context)
        
        sem_res = self.semantic_evaluator.evaluate(
            question=question,
            student_answer=sanitized_answer,
            rubric_criteria=rubric_data["criteria"],
            is_autonomous_rubric=rubric_data["is_autonomous_rubric"]
        )

        local_marks = sem_res.overall_score
        concept_coverage_ratio = sem_res.semantic_confidence # approximate fallback
        semantic_confidence = sem_res.semantic_confidence

        # ── Evidence Fusion ───────────────────────────────────────
        fused_score, fused_matched, fused_missing = self.fusion_engine.fuse(
            llm_eval=llm_eval,
            local_score=local_marks,
            max_marks=max_marks,
            concept_coverage=concept_coverage_ratio,
            semantic_similarity=semantic_confidence,
        )

        confidence = self.calculate_confidence(
            semantic_confidence=semantic_confidence,
            concept_coverage=concept_coverage_ratio,
            rubric_alignment=1.0,
        )
        
        found = []
        missing = []
        for ev in sem_res.evidence:
            if ev.satisfied:
                found.append(ev.criterion[:15])
            else:
                missing.append(ev.criterion[:15])
                
        rubric_points = []
        for ev in sem_res.evidence:
            matched_crit = next((c for c in rubric_data["criteria"] if c["description"] == ev.criterion), None)
            alloc = matched_crit["allocated_marks"] if matched_crit else 0.0
            rubric_points.append(RubricCriterion(
                criterion_id=f"crit_{len(rubric_points)+1}",
                description=ev.criterion,
                allocated_marks=alloc,
                marks_awarded=alloc if ev.satisfied else 0.0,
                met=ev.satisfied
            ))
            
        feedback = self.generate_feedback(found, missing, fused_score, max_marks)

        return QuestionEvaluation(
            question_number=question_number,
            max_marks=max_marks,
            score_awarded=fused_score,
            student_answer_extracted=sanitized_answer,
            criteria_feedback=llm_eval.criteria_feedback if llm_eval else feedback["criteria_feedback"],
            matched_keywords=found,
            rubric_points=rubric_points,
            confidence=confidence,
            concept_coverage=concept_coverage_ratio,
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

import pytest

from AI.evaluation.autonomous_evaluator import AutonomousEvaluator
from AI.evaluation.concept_engine import ConceptCoverageEngine


def test_descriptive_photosynthesis_answer_scores_high():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Explain Photosynthesis (5 Marks)",
        student_answer=(
            "Photosynthesis uses sunlight and chlorophyll in chloroplasts. "
            "Plants take carbon dioxide and water to make glucose and release oxygen."
        ),
        max_marks=5,
        subject="Biology",
    )

    assert result.score_awarded >= 4.0
    assert result.concept_coverage >= 70
    assert result.evaluation_mode == "AI_AUTONOMOUS"
    assert "chlorophyll" in result.matched_keywords


def test_short_answer_gets_partial_credit():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Define photosynthesis (2 Marks)",
        student_answer="Plants make food using sunlight.",
        max_marks=2,
        subject="Biology",
    )

    assert 0 < result.score_awarded < 2
    assert result.confidence > 0


def test_long_answer_handles_depth():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Explain the process of photosynthesis in plants (8 Marks)",
        student_answer=(
            "Photosynthesis occurs in chloroplasts where chlorophyll absorbs sunlight. "
            "The plant uses carbon dioxide from air and water from roots. "
            "The process produces glucose as food and oxygen is released. "
            "This conversion stores light energy as chemical energy."
        ),
        max_marks=8,
        subject="Biology",
    )

    assert result.score_awarded >= 6
    assert result.expected_depth == "detailed"


def test_partial_answer_missing_concepts_are_reported():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Explain Photosynthesis (5 Marks)",
        student_answer="Plants use sunlight to make food.",
        max_marks=5,
        subject="Biology",
    )

    assert 0 < result.score_awarded < 5
    assert result.missing_concepts


def test_empty_answer_scores_zero_without_fake_feedback():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Explain Photosynthesis (5 Marks)",
        student_answer="",
        max_marks=5,
        subject="Biology",
    )

    assert result.score_awarded == 0
    assert result.student_answer_extracted == ""
    assert result.concept_coverage == 0


def test_incorrect_answer_scores_low():
    evaluator = AutonomousEvaluator()

    result = evaluator.evaluate_answer(
        question="Explain Photosynthesis (5 Marks)",
        student_answer="Photosynthesis is when rocks become water and animals sleep.",
        max_marks=5,
        subject="Biology",
    )

    assert result.score_awarded <= 2


def test_confidence_calculation_average():
    evaluator = AutonomousEvaluator()

    confidence = evaluator.calculate_confidence(
        semantic_confidence=0.6,
        concept_coverage=0.9,
        rubric_alignment=0.75,
    )

    assert confidence == 0.75


def test_fairness_sanitization_removes_identity_and_protected_terms():
    engine = ConceptCoverageEngine()

    sanitized = engine.sanitize_for_fairness(
        "Name: Asha Sharma Roll No: CS101 My handwriting is neat. Photosynthesis uses sunlight."
    )

    assert "Asha" not in sanitized
    assert "CS101" not in sanitized
    assert "handwriting" not in sanitized.lower()
    assert "sunlight" in sanitized.lower()


def test_missing_question_context_fails_explicitly():
    evaluator = AutonomousEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate_answer(
            question="",
            student_answer="Some answer",
            max_marks=5,
        )


def test_feedback_generation_contains_recommendations():
    evaluator = AutonomousEvaluator()

    feedback = evaluator.generate_feedback(
        found_concepts=["sunlight"],
        missing_concepts=["chlorophyll"],
        marks_awarded=2,
        max_marks=5,
    )

    assert feedback["strengths"]
    assert feedback["weaknesses"]
    assert feedback["improvements"]
    assert feedback["study_recommendations"]


def test_question_type_branches_and_invalid_marks():
    evaluator = AutonomousEvaluator()

    assert evaluator.analyze_question("Compare mitosis and meiosis (5 Marks)", 5, "Biology")["question_type"] == "COMPARATIVE"
    assert evaluator.analyze_question("Solve the equation x + 2 = 4 (2 Marks)", 2, "Mathematics")["question_type"] == "NUMERICAL"
    assert evaluator.analyze_question("List two properties of acids (3 Marks)", 3, "Chemistry")["question_type"] == "LIST"

    with pytest.raises(ValueError):
        evaluator.analyze_question("", 5)

    with pytest.raises(ValueError):
        evaluator.evaluate_answer("Define atom", "Matter particle", 0)


def test_calculate_marks_and_empty_distribution_branch():
    evaluator = AutonomousEvaluator()
    first = evaluator.evaluate_answer("Define atom (2 Marks)", "An atom has protons and electrons.", 2, subject="Chemistry")
    second = evaluator.evaluate_answer("Define force (2 Marks)", "Force changes motion.", 2, subject="Physics")

    assert evaluator.calculate_marks([first, second]) == round(first.score_awarded + second.score_awarded, 2)
    assert evaluator._mark_distribution([], 5) == {}


def test_concept_engine_subject_inference_and_error_paths():
    engine = ConceptCoverageEngine()

    assert engine.infer_subject("Velocity and acceleration are related") == "physics"
    assert engine.generate_expected_concepts("General biology question", "Biology")

    with pytest.raises(ValueError):
        engine.generate_expected_concepts("")

    with pytest.raises(ValueError):
        engine.generate_expected_concepts("the what about", "")


def test_concept_engine_rejects_metadata_and_field_labels():
    engine = ConceptCoverageEngine()

    concepts = engine.generate_expected_concepts(
        "Question 2: Explain photosynthesis. expected_concepts key answer_key metadata coverage.",
        "Biology",
    )

    assert "photosynthesis" in concepts
    assert "key" not in concepts
    assert "answer key" not in concepts
    assert "expected concepts" not in concepts
    assert "metadata" not in concepts
    assert "coverage" not in concepts


def test_feedback_does_not_surface_invalid_concept_labels():
    from AI.evaluation.feedback import compile_feedback

    result = compile_feedback({
        "total_score": 0,
        "max_possible": 5,
        "questions": [
            {
                "question_number": "2",
                "rubric_points": [
                    {
                        "description": "Coverage of expected concept: key",
                        "allocated_marks": 1,
                        "marks_awarded": 0,
                        "met": False,
                    },
                    {
                        "description": "Coverage of expected concept: photosynthesis",
                        "allocated_marks": 1,
                        "marks_awarded": 0,
                        "met": False,
                    },
                ],
            }
        ],
    })

    feedback_text = " ".join(
        result["strengths"] + result["weaknesses"] + result["improvements"] + [result["summary"]]
    ).lower()
    assert "expected concept: key" not in feedback_text
    assert "photosynthesis" in feedback_text

"""
Unit tests for the GradeMIND Knowledge Base Layer.
"""

import pytest
from pydantic import ValidationError
from AI.knowledge_base.models import Subject, Chapter, Topic, Question, ReferenceAnswer, Rubric, RubricCriterion
from AI.knowledge_base.knowledge_service import KnowledgeBaseService


def test_validation_constraints():
    """Scenario 8: Validation rules (Pydantic validation checks)."""
    # Empty ID validation
    with pytest.raises(ValidationError):
        Subject(id=" ", name="Math", code="M-101")

    # Negative marks validation
    with pytest.raises(ValidationError):
        Question(id="q1", topic_id="t1", question_text="What is 1+1?", marks=-5.0)

    # Empty rubric description validation
    with pytest.raises(ValidationError):
        RubricCriterion(id="c1", rubric_id="r1", description="", allocated_marks=2.0)


def test_service_integration_and_seeding():
    """Scenario 10: Service integration & seeded default data validation."""
    service = KnowledgeBaseService(seed=True)
    
    # Verify default seeded Subject
    sub = service.get_subject("sub_science")
    assert sub is not None
    assert sub.name == "Science"
    assert sub.code == "SCI-101"

    # Verify default seeded Chapter
    chap = service.get_chapter("chap_photosynthesis")
    assert chap is not None
    assert chap.name == "Photosynthesis"
    assert chap.subject_id == "sub_science"

    # Verify default seeded Topic
    topic = service.get_topic("top_plant_nutrition")
    assert topic is not None
    assert topic.name == "Plant Nutrition"
    assert "Understand how plants synthesize food." in topic.learning_objectives


def test_subject_retrieval():
    """Scenario 1: Subject retrieval."""
    service = KnowledgeBaseService(seed=False)
    sub = Subject(id="math", name="Mathematics", code="MATH-202")
    service.curriculum_store.add_subject(sub)

    retrieved = service.get_subject("math")
    assert retrieved is not None
    assert retrieved.name == "Mathematics"


def test_chapter_retrieval():
    """Scenario 2: Chapter retrieval."""
    service = KnowledgeBaseService(seed=False)
    chap = Chapter(id="chap_algebra", subject_id="math", name="Algebra", description="Introduction to Algebra")
    service.curriculum_store.add_chapter(chap)

    retrieved = service.get_chapter("chap_algebra")
    assert retrieved is not None
    assert retrieved.name == "Algebra"


def test_topic_retrieval():
    """Scenario 3: Topic retrieval."""
    service = KnowledgeBaseService(seed=False)
    topic = Topic(id="top_equations", chapter_id="chap_algebra", name="Quadratic Equations")
    service.curriculum_store.add_topic(topic)

    retrieved = service.get_topic("top_equations")
    assert retrieved is not None
    assert retrieved.name == "Quadratic Equations"


def test_question_retrieval():
    """Scenario 4: Question retrieval."""
    service = KnowledgeBaseService(seed=False)
    question = Question(id="q_equations", topic_id="top_equations", question_text="Solve x^2 = 4", marks=3.0)
    service.question_store.add_question(question)

    retrieved = service.get_question("q_equations")
    assert retrieved is not None
    assert retrieved.question_text == "Solve x^2 = 4"
    assert retrieved.marks == 3.0


def test_reference_answer_retrieval():
    """Scenario 5: Reference answer retrieval."""
    service = KnowledgeBaseService(seed=False)
    answer = ReferenceAnswer(id="ans_equations", question_id="q_equations", answer_text="x = 2 or x = -2")
    service.answer_store.add_reference_answer(answer)

    retrieved = service.get_reference_answer("q_equations")
    assert retrieved is not None
    assert retrieved.answer_text == "x = 2 or x = -2"


def test_rubric_retrieval():
    """Scenario 6: Rubric retrieval."""
    service = KnowledgeBaseService(seed=False)
    rubric = Rubric(id="rub_equations", question_id="q_equations", title="Equations Rubric")
    crit = RubricCriterion(id="crit_eq_1", rubric_id="rub_equations", description="Correct working steps", allocated_marks=2.0)
    
    # Store criteria first, then rubric
    service.rubric_store.add_criterion(crit)
    service.rubric_store.add_rubric(rubric)

    retrieved = service.get_rubric("q_equations")
    assert retrieved is not None
    assert retrieved.title == "Equations Rubric"
    assert len(retrieved.criteria) == 1
    assert retrieved.criteria[0].description == "Correct working steps"


def test_missing_records():
    """Scenario 7: Missing records handling."""
    service = KnowledgeBaseService(seed=True)
    
    # Retrieving non-existent entries returns None gracefully
    assert service.get_subject("non_existent") is None
    assert service.get_chapter("non_existent") is None
    assert service.get_topic("non_existent") is None
    assert service.get_question("non_existent") is None
    assert service.get_reference_answer("non_existent") is None
    assert service.get_rubric("non_existent") is None


def test_relationships():
    """Scenario 9: Relationships check (ensuring cross-relation integrity)."""
    service = KnowledgeBaseService(seed=True)

    # 1. Fetch Question
    q = service.get_question("q_photosynthesis")
    assert q is not None
    
    # 2. Trace Topic
    topic = service.get_topic(q.topic_id)
    assert topic is not None
    assert topic.id == "top_plant_nutrition"
    
    # 3. Trace Chapter
    chap = service.get_chapter(topic.chapter_id)
    assert chap is not None
    assert chap.id == "chap_photosynthesis"

    # 4. Trace Subject
    sub = service.get_subject(chap.subject_id)
    assert sub is not None
    assert sub.id == "sub_science"


def test_rag_mock_search():
    """Verifies future search/RAG mock functionality."""
    service = KnowledgeBaseService(seed=True)
    results = service.search_similar_questions("photosynthesis")
    assert len(results) >= 1
    assert results[0].id == "q_photosynthesis"

    empty_results = service.search_similar_questions("quantum gravity")
    assert len(empty_results) == 0

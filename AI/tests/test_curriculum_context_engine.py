"""
Unit and integration tests for the Curriculum Context Engine.
Covers 10 scenarios as per Day 8 requirements.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock
from AI.schemas.evaluation_schema import QuestionEvaluation, RubricCriterion
from AI.rag.embedding_service import EmbeddingService
from AI.rag.rag_service import RAGService
from AI.knowledge_base.knowledge_service import KnowledgeBaseService
from AI.evaluation.curriculum_context_engine import CurriculumContextEngine
from AI.evaluation.semantic_engine import SemanticEvaluationEngine
from AI.evaluation.gemini_evaluator import GeminiEvaluator


@pytest.fixture
def mock_embedding_service():
    """Provides a mocked embedding service returning distinct vectors per text."""
    service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    mock_eval_service = MagicMock()
    
    def generate_emb(text):
        # Deterministic vector based on text content to simulate query similarity
        val = (sum(ord(c) for c in text) % 100) / 100.0
        vec = np.zeros(384, dtype=np.float32)
        vec[0] = val
        vec[1] = 1.0 - val
        # Normalize to unit vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
        
    mock_eval_service.generate_embedding.side_effect = generate_emb
    mock_eval_service.generate_batch_embeddings.side_effect = lambda texts: [
        generate_emb(t) for t in texts
    ]
    service._service = mock_eval_service
    return service


def test_context_retrieval(mock_embedding_service):
    """Scenario 1: Context retrieval & Scenario 10: End-to-end context generation."""
    kb_service = KnowledgeBaseService(seed=True)
    rag_service = RAGService(embedding_service=mock_embedding_service)
    
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    context = engine.build_context("What is photosynthesis?")
    
    assert context.subject == "Science (SCI-101). General Science Curriculum"
    assert context.chapter == "Photosynthesis. Understanding energy conversion in plants."
    assert context.topic == "Plant Nutrition. Objectives: Understand how plants synthesize food.; Describe the role of light, chlorophyll, and water."
    assert "photosynthesis" in context.reference_answer.lower()
    assert context.rubric == "Photosynthesis Evaluation Rubric"
    assert len(context.rubric_criteria) == 3
    assert context.retrieval_score > 0.0


def test_missing_curriculum(mock_embedding_service):
    """Scenario 2: Missing curriculum & Scenario 8: Empty KB."""
    # Create empty KB
    kb_service = KnowledgeBaseService(seed=False)
    rag_service = RAGService(embedding_service=mock_embedding_service)
    
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    context = engine.build_context("What is quantum computing?")
    
    # Assert it returns a graceful empty context
    assert context.subject == ""
    assert context.reference_answer == ""
    assert context.rubric == ""
    assert len(context.rubric_criteria) == 0
    assert context.retrieval_score == 0.0


def test_partial_retrieval(mock_embedding_service):
    """Scenario 3: Partial retrieval & Scenario 4: Reference answer & Scenario 5: Rubric retrieval."""
    kb_service = KnowledgeBaseService(seed=False)
    
    # Seed only Subject and Reference Answer, no topic/rubric
    from AI.knowledge_base.models import Subject, ReferenceAnswer
    kb_service.curriculum_store.add_subject(Subject(id="sub_1", name="Math", code="M1"))
    kb_service.answer_store.add_reference_answer(ReferenceAnswer(id="ans_1", question_id="q1", answer_text="42"))
    
    rag_service = RAGService(embedding_service=mock_embedding_service)
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    
    context = engine.build_context("What is the answer?")
    
    # Should resolve partial components successfully
    assert "Math" in context.subject
    assert context.reference_answer == "42"
    assert context.chapter == ""
    assert context.rubric == ""
    assert len(context.rubric_criteria) == 0


def test_gemini_integration(mock_embedding_service):
    """Scenario 6: Gemini integration verification."""
    kb_service = KnowledgeBaseService(seed=True)
    rag_service = RAGService(embedding_service=mock_embedding_service)
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    context = engine.build_context("What is photosynthesis?")

    # Instantiating GeminiEvaluator and mocking generative AI model calls
    evaluator = GeminiEvaluator(model_name="gemini-3.5-flash")
    evaluator._client_configured = True
    evaluator.model = MagicMock()
    
    mock_response = MagicMock()
    mock_response.text = '{"score": 5.0, "confidence": 0.9, "reasoning": "Correct", "strengths": ["Paraphrasing"], "weaknesses": [], "missing_concepts": []}'
    evaluator.model.generate_content.return_value = mock_response

    rubric_point = RubricCriterion(criterion_id="crit_1", description="Definition", allocated_marks=2.0)
    
    res = evaluator.evaluate(
        question="What is photosynthesis?",
        student_answer="Plants convert light into chemical energy.",
        rubric_points=[rubric_point],
        expected_concepts=["light"],
        max_marks=2.0,
        curriculum_context=context
    )
    
    assert res is not None
    assert res.score == 5.0
    
    # Verify model generate content was called with context details
    evaluator.model.generate_content.assert_called()
    called_prompt = evaluator.model.generate_content.call_args[0][0]
    assert "CURRICULUM CONTEXT" in called_prompt
    assert "Science" in called_prompt
    assert "Plant Nutrition" in called_prompt


def test_semantic_integration(mock_embedding_service):
    """Scenario 7: Semantic integration verification."""
    kb_service = KnowledgeBaseService(seed=True)
    rag_service = RAGService(embedding_service=mock_embedding_service)
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    context = engine.build_context("What is photosynthesis?")

    semantic_engine = SemanticEvaluationEngine(embedding_service=mock_embedding_service)
    
    # Perform evaluate passing topic/chapter context
    res = semantic_engine.evaluate(
        question="What is photosynthesis?",
        reference_answer=context.reference_answer,
        student_answer="Plants make food from sun.",
        expected_concepts=["convert sunlight"],
        topic_context=context.topic,
        chapter_context=context.chapter
    )
    assert res is not None
    assert res.semantic_similarity >= 0.0


def test_multi_topic_retrieval(mock_embedding_service):
    """Scenario 9: Multi-topic retrieval verification."""
    kb_service = KnowledgeBaseService(seed=False)
    
    # Seed multiple topics
    from AI.knowledge_base.models import Topic
    kb_service.curriculum_store.add_topic(Topic(id="top_1", chapter_id="c1", name="Cell Respiration"))
    kb_service.curriculum_store.add_topic(Topic(id="top_2", chapter_id="c1", name="Cell Division"))
    
    rag_service = RAGService(embedding_service=mock_embedding_service)
    engine = CurriculumContextEngine(rag_service=rag_service, kb_service=kb_service)
    
    context = engine.build_context("Explain respiration and division")
    # Will retrieve topics matching the query
    assert context.topic != ""

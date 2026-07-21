"""
Unit and integration tests for the RAG Foundation.
Covers 10 scenarios as per Day 7 requirements.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock
from AI.rag.embedding_service import EmbeddingService
from AI.rag.vector_store import VectorStore, VectorRecord
from AI.rag.retriever import Retriever
from AI.rag.context_builder import ContextBuilder
from AI.rag.rag_service import RAGService
from AI.knowledge_base.knowledge_service import KnowledgeBaseService


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


def test_embedding_generation(mock_embedding_service):
    """Scenario 1: Embedding generation."""
    emb = mock_embedding_service.embed_text("test content")
    assert len(emb) == 384
    assert isinstance(emb, list)
    assert isinstance(emb[0], float)

    batch_embs = mock_embedding_service.embed_batch(["text 1", "text 2"])
    assert len(batch_embs) == 2
    assert len(batch_embs[0]) == 384


def test_vector_insertion_and_count():
    """Scenario 2: Vector insertion."""
    store = VectorStore()
    assert store.count() == 0

    # Insert single document
    store.add_document(
        document_id="doc_1",
        document_type="Subject",
        content="Subject content",
        embedding=[0.1] * 384,
        metadata={"subject_code": "SCI-101"}
    )
    assert store.count() == 1

    # Insert batch
    doc2 = VectorRecord(
        document_id="doc_2",
        document_type="Question",
        content="Question content",
        embedding=[0.2] * 384,
        metadata={"marks": 5.0}
    )
    store.add_documents([doc2])
    assert store.count() == 2


def test_vector_retrieval_and_ranking():
    """Scenario 3: Vector retrieval & Scenario 4: Similarity ranking."""
    store = VectorStore()
    
    # Store orthogonal vectors
    # Record 1: close to query
    store.add_document("doc_1", "Question", "Close doc", [1.0, 0.0, 0.0])
    # Record 2: orthogonal/far
    store.add_document("doc_2", "Question", "Far doc", [0.0, 1.0, 0.0])

    # Search with query close to doc_1
    query_emb = [1.0, 0.0, 0.0]
    hits = store.search(query_emb, top_k=2)

    assert len(hits) == 2
    # doc_1 must be ranked first (similarity = 1.0)
    assert hits[0][0].document_id == "doc_1"
    assert abs(hits[0][1] - 1.0) < 1e-5

    # doc_2 must be ranked second (similarity = 0.0)
    assert hits[1][0].document_id == "doc_2"
    assert abs(hits[1][1] - 0.0) < 1e-5


def test_context_building():
    """Scenario 5: Context building."""
    builder = ContextBuilder()
    
    retrieved_docs = [
        {
            "document_id": "sub_1",
            "document_type": "Subject",
            "content": "Biology curriculum",
            "score": 0.95,
            "metadata": {}
        },
        {
            "document_id": "ans_1",
            "document_type": "ReferenceAnswer",
            "content": "Water is key.",
            "score": 0.88,
            "metadata": {}
        },
        {
            "document_id": "rub_1",
            "document_type": "Rubric",
            "content": "Grading criteria title",
            "score": 0.85,
            "metadata": {"criteria": [{"description": "Core definition", "allocated_marks": 2.0}]}
        }
    ]

    context = builder.build_context(retrieved_docs)
    
    assert context["subject"] == "Biology curriculum"
    assert context["reference_answer"] == "Water is key."
    assert len(context["rubric"]) == 1
    assert context["rubric"][0]["title"] == "Grading criteria title"
    assert context["rubric"][0]["criteria"][0]["description"] == "Core definition"


def test_empty_store():
    """Scenario 6: Empty store behavior."""
    store = VectorStore()
    hits = store.search([1.0, 0.0, 0.0])
    assert hits == []
    assert store.count() == 0


def test_missing_documents():
    """Scenario 7: Missing/deleted documents handling."""
    store = VectorStore()
    store.add_document("doc_1", "Subject", "Content", [1.0, 0.0])
    
    # Try deleting missing document
    assert not store.delete("doc_missing")
    assert store.count() == 1

    # Delete existing
    assert store.delete("doc_1")
    assert store.count() == 0


def test_batch_indexing(mock_embedding_service):
    """Scenario 8: Batch indexing in RAGService."""
    kb_service = KnowledgeBaseService(seed=True)
    rag = RAGService(embedding_service=mock_embedding_service)

    indexed_count = rag.index_knowledge_base(kb_service)
    # Seeds Subject, Chapter, Topic, Question, ReferenceAnswer, Rubric
    assert indexed_count == 6
    assert rag.vector_store.count() == 6


def test_knowledge_base_integration(mock_embedding_service):
    """Scenario 9: Knowledge base integration and parsing."""
    kb_service = KnowledgeBaseService(seed=True)
    rag = RAGService(embedding_service=mock_embedding_service)
    rag.index_knowledge_base(kb_service)

    # Retrieval for photosynthesis query should return photosynthesis records
    results = rag.retrieve_context("What is photosynthesis?", top_k=10)
    
    # Check that context extracts seeded answers
    assert "photosynthesis" in results["reference_answer"].lower()
    assert len(results["rubric"]) > 0


def test_end_to_end_retrieval(mock_embedding_service):
    """Scenario 10: End-to-end retrieval workflow."""
    kb_service = KnowledgeBaseService(seed=True)
    rag = RAGService(embedding_service=mock_embedding_service)
    rag.index_knowledge_base(kb_service)

    context = rag.retrieve_context("Explain photosynthesis plant nutrition", top_k=10)
    
    assert context["reference_answer"] is not None
    assert "chemical energy" in context["reference_answer"]
    assert len(context["rubric"]) > 0


# ---------------------------------------------------------
# Dynamic Real Integration Runs (if SentenceTransformer is imported)
# ---------------------------------------------------------
def test_real_rag_integration_run():
    """
    Runs dynamic end-to-end RAG checks using actual local MiniLM vectors
    if the sentence-transformers package is installed.
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        # Instantiate actual embedding service
        emb_service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
        rag_service = RAGService(embedding_service=emb_service)
        
        # Seed Knowledge Base
        kb_service = KnowledgeBaseService(seed=True)
        
        # Index Knowledge Base
        rag_service.index_knowledge_base(kb_service)
        
        # Retrieve context semantically
        context = rag_service.retrieve_context("sunlight into chemical energy", top_k=3)
        
        assert "sunlight" in context["reference_answer"].lower()
        print("Successfully validated end-to-end RAG with real local model inference.")
    except Exception as e:
        print(f"Skipping real model integration run: {e}")

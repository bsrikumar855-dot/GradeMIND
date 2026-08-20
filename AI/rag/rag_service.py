"""
RAG Service for GradeMIND.
Coordinates batch indexing and contextual retrieval for evaluation pipelines.
"""

import logging
from typing import Dict, Any, List, Optional
from AI.knowledge_base.knowledge_service import KnowledgeBaseService
from AI.rag.embedding_service import EmbeddingService
from AI.rag.vector_store import VectorStore
from AI.rag.retriever import Retriever
from AI.rag.context_builder import ContextBuilder

logger = logging.getLogger("GradeMIND.RAGService")


class RAGService:
    """
    Unified coordinator service for vector store indexing and RAG operations.
    """

    def __init__(
        self, 
        embedding_service: Optional[EmbeddingService] = None, 
        vector_store: Optional[VectorStore] = None
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.retriever = Retriever(self.embedding_service, self.vector_store)
        self.context_builder = ContextBuilder()

    def index_knowledge_base(self, kb_service: KnowledgeBaseService) -> int:
        """
        Extracts all curriculum knowledge components, builds text chunks,
        batch generates embeddings, and indexes them in the vector store.
        """
        logger.info("Starting batch indexing of GradeMIND Knowledge Base...")
        
        # Accumulator for batch processing
        # List of Tuple[doc_id, doc_type, text_content, metadata]
        index_queue = []

        # 1. Subjects
        for subject in kb_service.curriculum_store.list_subjects():
            content = f"Subject: {subject.name} ({subject.code}). {subject.description}".strip()
            index_queue.append((
                subject.id, 
                "Subject", 
                content, 
                {"id": subject.id, "name": subject.name, "code": subject.code, "subject_name": subject.name}
            ))

        # 2. Chapters
        for chapter in kb_service.curriculum_store.list_chapters():
            subject = kb_service.curriculum_store.get_subject(chapter.subject_id)
            sub_name = subject.name if subject else ""
            content = f"Chapter: {chapter.name}. {chapter.description}".strip()
            index_queue.append((
                chapter.id, 
                "Chapter", 
                content, 
                {"id": chapter.id, "subject_id": chapter.subject_id, "name": chapter.name, "subject_name": sub_name}
            ))

        # 3. Topics
        for topic in kb_service.curriculum_store.list_topics():
            chapter = kb_service.curriculum_store.get_chapter(topic.chapter_id)
            subject = kb_service.curriculum_store.get_subject(chapter.subject_id) if chapter else None
            sub_name = subject.name if subject else ""
            
            objectives = "; ".join(topic.learning_objectives)
            content = f"Topic: {topic.name}. Objectives: {objectives}".strip()
            index_queue.append((
                topic.id, 
                "Topic", 
                content, 
                {"id": topic.id, "chapter_id": topic.chapter_id, "name": topic.name, "subject_name": sub_name, "learning_objectives": topic.learning_objectives}
            ))

        # 4. Questions
        for question in kb_service.question_store.list_questions():
            content = f"Question: {question.question_text} (Difficulty: {question.difficulty}, Marks: {question.marks})".strip()
            index_queue.append((
                question.id, 
                "Question", 
                content, 
                {"id": question.id, "topic_id": question.topic_id, "marks": question.marks, "difficulty": question.difficulty}
            ))

        # 5. Reference Answers
        for answer in kb_service.answer_store.list_reference_answers():
            content = f"Reference Answer: {answer.answer_text}".strip()
            index_queue.append((
                answer.id, 
                "ReferenceAnswer", 
                content, 
                {"id": answer.id, "question_id": answer.question_id}
            ))

        # 6. Rubrics
        for rubric in kb_service.rubric_store.list_rubrics():
            content = f"Rubric for Question: {rubric.title}".strip()
            criteria_data = [
                {"description": c.description, "allocated_marks": c.allocated_marks}
                for c in rubric.criteria
            ]
            index_queue.append((
                rubric.id, 
                "Rubric", 
                content, 
                {"id": rubric.id, "question_id": rubric.question_id, "criteria": criteria_data}
            ))

        if not index_queue:
            logger.warning("No knowledge base elements found to index.")
            return 0

        # Extract texts for batch embedding
        texts_to_embed = [item[2] for item in index_queue]
        
        # Batch generate embeddings
        logger.info("Generating batch embeddings for %d curriculum items...", len(texts_to_embed))
        embeddings = self.embedding_service.embed_batch(texts_to_embed)

        # Add to vector store
        for idx, (doc_id, doc_type, content, metadata) in enumerate(index_queue):
            self.vector_store.add_document(
                document_id=doc_id,
                document_type=doc_type,
                content=content,
                embedding=embeddings[idx],
                metadata=metadata
            )

        logger.info("Successfully indexed %d documents into Vector Store.", len(index_queue))
        return len(index_queue)

    def retrieve_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Retrieves matching documents for the query and builds a structured
        curriculum-aware context payload for evaluation.
        """
        # Retrieve ranked results
        retrieved_docs = self.retriever.retrieve(query, top_k=top_k)
        
        # Build structured evaluation context
        return self.context_builder.build_context(retrieved_docs, query=query)

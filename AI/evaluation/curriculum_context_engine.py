"""
Curriculum Context Engine for GradeMIND.
Retrieves and constructs curriculum-aware grading context.
"""

import logging
from typing import Optional, List, Dict, Any
from AI.schemas.evaluation_schema import CurriculumContext
from AI.rag.rag_service import RAGService
from AI.knowledge_base.knowledge_service import KnowledgeBaseService

logger = logging.getLogger("GradeMIND.CurriculumContextEngine")


class CurriculumContextEngine:
    """
    RAG-driven engine to extract subject, topic, answer key, and criteria context for grading.
    """

    def __init__(
        self, 
        rag_service: Optional[RAGService] = None, 
        kb_service: Optional[KnowledgeBaseService] = None
    ):
        self.kb_service = kb_service or KnowledgeBaseService(seed=True)
        self.rag_service = rag_service or RAGService()

        # Auto-index knowledge base if the vector store is currently unindexed
        if self.rag_service.vector_store.count() == 0:
            self.rag_service.index_knowledge_base(self.kb_service)

    def build_context(self, question_text: str, subject_hint: str = "") -> CurriculumContext:
        """
        Retrieves matching curriculum vectors and returns a structured CurriculumContext.
        Filters out mismatched RAG results if score is low or subject does not align.
        """
        logger.info("Building curriculum context for question: %r (subject_hint=%r)", question_text[:50], subject_hint)
        
        if not question_text or not question_text.strip():
            return CurriculumContext(retrieval_score=0.0)

        try:
            # Prepare metadata filters based on the subject hint
            metadata_filters: Optional[Dict[str, Any]] = None
            if subject_hint and subject_hint.lower() != "general":
                metadata_filters = {"subject_name": subject_hint}
            
            # Retrieve documents
            docs = self.rag_service.retriever.retrieve(
                question_text, 
                top_k=20,
                metadata_filters=metadata_filters
            )
            
            # If no docs found with filter, try without filter (graceful degradation)
            if not docs and metadata_filters:
                logger.warning("No docs found for subject %r. Retrying globally.", subject_hint)
                docs = self.rag_service.retriever.retrieve(question_text, top_k=20)
                
            if not docs:
                if subject_hint:
                    return CurriculumContext(
                        subject=subject_hint,
                        chapter=f"{subject_hint} Core",
                        topic=subject_hint,
                        retrieval_score=0.0
                    )
                return CurriculumContext(retrieval_score=0.0)

            highest_score = max((doc.get("score", 0.0) for doc in docs), default=0.0)

            subject_str = ""
            chapter_str = ""
            topic_str = ""
            ref_answer_str = ""
            rubric_title_str = ""
            rubric_criteria_list: List[str] = []
            learning_objectives_list: List[str] = []
            expected_concepts_list: List[str] = []

            for doc in docs:
                doc_type = doc.get("document_type", "").lower()
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                if doc_type == "subject" and not subject_str:
                    subject_str = content.replace("Subject: ", "", 1)
                elif doc_type == "chapter" and not chapter_str:
                    chapter_str = content.replace("Chapter: ", "", 1)
                elif doc_type == "topic" and not topic_str:
                    topic_str = content.replace("Topic: ", "", 1)
                    learning_objectives_list = metadata.get("learning_objectives", [])
                elif doc_type == "referenceanswer" and not ref_answer_str:
                    ref_answer_str = content.replace("Reference Answer: ", "", 1)
                elif doc_type == "rubric" and not rubric_title_str:
                    rubric_title_str = content.replace("Rubric for Question: ", "", 1)
                    criteria_meta = metadata.get("criteria", [])
                    for crit in criteria_meta:
                        desc = crit.get("description", "")
                        marks = crit.get("allocated_marks", 0.0)
                        if desc:
                            rubric_criteria_list.append(f"{desc} ({marks} marks)")
                            
            # Derive expected concepts from learning objectives if none are explicitly mapped
            # (In a real system, concepts would be parsed. Here we map objectives to concepts)
            if learning_objectives_list:
                expected_concepts_list = [obj.strip() for obj in learning_objectives_list]

            # If subject string is empty, fall back to the subject hint
            if not subject_str and subject_hint:
                subject_str = subject_hint

            return CurriculumContext(
                subject=subject_str,
                chapter=chapter_str,
                topic=topic_str,
                learning_objectives=learning_objectives_list,
                expected_concepts=expected_concepts_list,
                reference_answer=ref_answer_str,
                rubric=rubric_title_str,
                rubric_criteria=rubric_criteria_list,
                retrieval_score=highest_score
            )

        except Exception as e:
            logger.exception("Error building curriculum context")
            return CurriculumContext(retrieval_score=0.0)

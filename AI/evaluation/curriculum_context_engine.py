"""
Curriculum Context Engine for GradeMIND.
Retrieves and constructs curriculum-aware grading context.
"""

import logging
from typing import Optional, List
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

    def build_context(self, question_text: str) -> CurriculumContext:
        """
        Retrieves matching curriculum vectors and returns a structured CurriculumContext.
        """
        logger.info("Building curriculum context for question: %r", question_text[:50])
        
        if not question_text or not question_text.strip():
            return CurriculumContext(retrieval_score=0.0)

        try:
            # Retrieve documents (use top_k=10 to ensure we capture all categories)
            docs = self.rag_service.retriever.retrieve(question_text, top_k=10)
            
            if not docs:
                return CurriculumContext(retrieval_score=0.0)

            # Find the highest retrieval score
            highest_score = max(doc.get("score", 0.0) for doc in docs)

            subject_str = ""
            chapter_str = ""
            topic_str = ""
            ref_answer_str = ""
            rubric_title_str = ""
            rubric_criteria_list: List[str] = []

            for doc in docs:
                doc_type = doc.get("document_type", "").lower()
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                if doc_type == "subject" and not subject_str:
                    # Strip prefixes if present
                    subject_str = content.replace("Subject: ", "", 1)
                
                elif doc_type == "chapter" and not chapter_str:
                    chapter_str = content.replace("Chapter: ", "", 1)
                
                elif doc_type == "topic" and not topic_str:
                    topic_str = content.replace("Topic: ", "", 1)
                
                elif doc_type == "referenceanswer" and not ref_answer_str:
                    ref_answer_str = content.replace("Reference Answer: ", "", 1)
                
                elif doc_type == "rubric" and not rubric_title_str:
                    rubric_title_str = content.replace("Rubric for Question: ", "", 1)
                    # Extract rubric criteria descriptions from metadata
                    criteria_meta = metadata.get("criteria", [])
                    for crit in criteria_meta:
                        desc = crit.get("description", "")
                        marks = crit.get("allocated_marks", 0.0)
                        if desc:
                            rubric_criteria_list.append(f"{desc} ({marks} marks)")

            return CurriculumContext(
                subject=subject_str,
                chapter=chapter_str,
                topic=topic_str,
                reference_answer=ref_answer_str,
                rubric=rubric_title_str,
                rubric_criteria=rubric_criteria_list,
                retrieval_score=highest_score
            )

        except Exception as e:
            logger.exception("Error building curriculum context")
            # Graceful fallback on exception
            return CurriculumContext(retrieval_score=0.0)

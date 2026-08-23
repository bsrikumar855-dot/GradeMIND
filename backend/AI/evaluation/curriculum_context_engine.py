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

    def build_context(self, question_text: str, subject_hint: str = "") -> CurriculumContext:
        """
        Retrieves matching curriculum vectors and returns a structured CurriculumContext.
        Filters out mismatched RAG results if score is low or subject does not align.
        """
        logger.info("Building curriculum context for question: %r (subject_hint=%r)", question_text[:50], subject_hint)
        
        if not question_text or not question_text.strip():
            return CurriculumContext(retrieval_score=0.0)

        try:
            # Retrieve documents (top_k=20 ensures all categories across subjects are captured)
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

            q_low = question_text.lower()
            
            # Filter docs by query intent if multiple subjects are indexed
            if "photo" in q_low or "science" in q_low or "plant" in q_low:
                target_docs = [d for d in docs if any(w in d.get("content", "").lower() for w in ["photo", "science", "plant", "nutrition"])]
                if target_docs:
                    docs = target_docs
            elif any(w in q_low for w in ["array", "linked", "stack", "queue", "tree", "graph", "dsa"]):
                target_docs = [d for d in docs if any(w in d.get("content", "").lower() for w in ["dsa", "structure", "array", "linked", "algorithm"])]
                if target_docs:
                    docs = target_docs

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

            # Check if retrieved subject aligns with subject_hint or question_text
            q_low = question_text.lower()
            is_dsa_q = any(k in q_low for k in ["array", "linked list", "stack", "queue", "tree", "graph", "pointer", "node", "dsa", "algorithm"])
            is_mismatched = False

            if subject_hint:
                sh_lower = subject_hint.lower()
                sub_lower = subject_str.lower()
                if ("dsa" in sh_lower or "structure" in sh_lower or "algo" in sh_lower or "computer" in sh_lower) and "science" in sub_lower:
                    is_mismatched = True
            elif is_dsa_q and "science" in subject_str.lower():
                is_mismatched = True

            if is_mismatched:
                clean_subject = subject_hint if subject_hint and subject_hint.lower() != "general" else "Data Structures & Algorithms"
                return CurriculumContext(
                    subject=clean_subject,
                    chapter="Linear & Non-Linear Data Structures",
                    topic="Data Structures & Algorithms",
                    reference_answer="",
                    rubric="",
                    rubric_criteria=[],
                    retrieval_score=highest_score
                )

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
            return CurriculumContext(retrieval_score=0.0)

        except Exception as e:
            logger.exception("Error building curriculum context")
            # Graceful fallback on exception
            return CurriculumContext(retrieval_score=0.0)

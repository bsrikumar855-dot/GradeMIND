"""
Semantic Evaluation Engine for GradeMIND.
Extracts semantic evidence using an LLM and scores similarity using local embeddings.
"""

import logging
from typing import List, Optional, Dict, Any

from AI.evaluation.embeddings import EmbeddingService
from AI.evaluation.similarity import SimilarityEngine
from AI.schemas.evaluation_schema import SemanticEvaluationResult, SemanticEvidence
from AI.evaluation.groq_evaluator import GroqEvaluator

logger = logging.getLogger("GradeMIND.SemanticEvaluationEngine")

class SemanticEvaluationEngine:
    """
    Evidence-based semantic assessment engine.
    Extracts evidence spans for rubric criteria and calculates semantic confidence.
    """

    def __init__(
        self, 
        embedding_service: Optional[EmbeddingService] = None, 
        similarity_engine: Optional[SimilarityEngine] = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.llm_evaluator = GroqEvaluator()

    def evaluate(
        self, 
        question: str, 
        student_answer: str, 
        rubric_criteria: List[Dict[str, Any]],
        is_autonomous_rubric: bool = False
    ) -> SemanticEvaluationResult:
        """
        Performs semantic evaluation using LLM evidence extraction and local embedding validation.
        """
        logger.info(
            "Starting semantic evidence evaluation. Criteria count: %d", 
            len(rubric_criteria)
        )
        
        clean_student = (student_answer or "").strip()
        
        # Calculate max marks
        max_score = sum(c.get("allocated_marks", 0.0) for c in rubric_criteria)
        
        # Handle empty/whitespace student answer
        if not clean_student:
            empty_evidence = []
            for c in rubric_criteria:
                empty_evidence.append(SemanticEvidence(
                    criterion=c["description"],
                    evidence_span="",
                    semantic_similarity=0.0,
                    satisfied=False,
                    confidence=1.0,
                    reason="Student answer is empty."
                ))
            return SemanticEvaluationResult(
                is_autonomous_rubric=is_autonomous_rubric,
                evidence=empty_evidence,
                overall_score=0.0,
                max_score=max_score,
                semantic_confidence=1.0,
                explanation="Student answer is empty. No evidence found."
            )

        if not self.llm_evaluator.is_available():
            logger.warning("GroqEvaluator is unavailable. Semantic evidence extraction cannot proceed.")
            return SemanticEvaluationResult(
                is_autonomous_rubric=is_autonomous_rubric,
                evidence=[],
                overall_score=0.0,
                max_score=max_score,
                semantic_confidence=0.0,
                explanation="LLM unavailable for semantic extraction."
            )

        try:
            criteria_strings = [c.get("description") or c.get("criterion", "") for c in rubric_criteria]
            extracted_evidence = self.llm_evaluator.extract_evidence(
                question=question,
                student_answer=clean_student,
                criteria=criteria_strings
            )
            
            evidence_models = []
            overall_score = 0.0
            
            # Map extracted items back to the rubric criteria
            extracted_map = {item.get("criterion", ""): item for item in extracted_evidence}
            
            # Pre-compute criterion embeddings for similarity
            try:
                crit_embs = self.embedding_service.generate_batch_embeddings(criteria_strings)
            except Exception as e:
                logger.warning("Failed to generate criterion embeddings: %s", e)
                crit_embs = [None] * len(criteria_strings)

            for idx, c in enumerate(rubric_criteria):
                desc = c.get("description") or c.get("criterion", "")
                alloc_marks = c.get("allocated_marks", 0.0)
                
                item = extracted_map.get(desc, {})
                evidence_span = item.get("evidence_span", "")
                satisfied = item.get("satisfied", False)
                confidence = item.get("confidence", 0.8)
                reason = item.get("reason", "No reason provided.")
                
                sim_score = 0.0
                if evidence_span and evidence_span.strip() and crit_embs[idx] is not None:
                    try:
                        ev_emb = self.embedding_service.generate_embedding(evidence_span)
                        crit_emb = crit_embs[idx]
                        sim_score = self.similarity_engine.calculate_similarity(crit_emb, ev_emb)
                    except Exception:
                        sim_score = 0.0
                        
                # Adjust satisfaction if the LLM hallucinated evidence
                if satisfied and not evidence_span.strip():
                    satisfied = False
                    reason = "LLM marked satisfied but provided no textual evidence."
                    
                if satisfied:
                    overall_score += alloc_marks
                    
                evidence_models.append(SemanticEvidence(
                    criterion=desc,
                    evidence_span=evidence_span,
                    semantic_similarity=round(sim_score, 4),
                    satisfied=satisfied,
                    confidence=confidence,
                    reason=reason
                ))
                
            overall_score = min(max(overall_score, 0.0), max_score)
            
            # Calculate overall semantic confidence based on LLM confidence and local similarity
            avg_conf = sum(e.confidence for e in evidence_models) / max(1, len(evidence_models))
            avg_sim = sum(e.semantic_similarity for e in evidence_models if e.satisfied) / max(1, sum(1 for e in evidence_models if e.satisfied))
            
            # If nothing satisfied, similarity is technically 0, but confidence in that 0 could be high.
            # We'll blend LLM confidence with similarity confidence.
            semantic_confidence = round(0.7 * avg_conf + 0.3 * (avg_sim if overall_score > 0 else 1.0), 4)

            # Construct explanation
            satisfied_count = sum(1 for e in evidence_models if e.satisfied)
            explanation = f"Semantically satisfied {satisfied_count}/{len(rubric_criteria)} criteria. Total score: {overall_score}/{max_score}."
            
            return SemanticEvaluationResult(
                is_autonomous_rubric=is_autonomous_rubric,
                evidence=evidence_models,
                overall_score=overall_score,
                max_score=max_score,
                semantic_confidence=semantic_confidence,
                explanation=explanation
            )
            
        except Exception as e:
            logger.exception("Exception during semantic evaluation process")
            return SemanticEvaluationResult(
                is_autonomous_rubric=is_autonomous_rubric,
                evidence=[],
                overall_score=0.0,
                max_score=max_score,
                semantic_confidence=0.0,
                explanation=f"Error performing semantic evaluation: {str(e)}"
            )

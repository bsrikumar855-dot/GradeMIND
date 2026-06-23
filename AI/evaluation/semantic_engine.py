"""
Semantic Evaluation Engine for GradeMIND.
Evaluates semantic similarity and concept matches using local embeddings.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from AI.evaluation.embeddings import EmbeddingService
from AI.evaluation.similarity import SimilarityEngine
from AI.schemas.evaluation_schema import SemanticEvaluationResult

logger = logging.getLogger("GradeMIND.SemanticEvaluationEngine")

class SemanticEvaluationEngine:
    """
    Additive semantic assessment engine.
    Compares student response against reference answer and expected concepts.
    """

    def __init__(
        self, 
        embedding_service: Optional[EmbeddingService] = None, 
        similarity_engine: Optional[SimilarityEngine] = None,
        concept_matching_threshold: float = 0.70
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.concept_matching_threshold = concept_matching_threshold

    def _split_into_segments(self, text: str) -> List[str]:
        """
        Splits text into sentences/phrases for localized semantic matching.
        """
        if not text:
            return []
        
        # Split on typical sentence boundaries and list indicators
        raw_segments = re.split(r'[.!?;\n]+', text)
        segments = []
        for segment in raw_segments:
            cleaned = segment.strip()
            # Filter out very short segments (e.g. less than 3 chars or just numbers)
            if len(cleaned) >= 3 and not cleaned.isdigit():
                segments.append(cleaned)
        
        # If no segments were found but text exists, return original text as single segment
        if not segments and text.strip():
            segments.append(text.strip())
            
        return segments

    def evaluate(
        self, 
        question: str, 
        reference_answer: str, 
        student_answer: str, 
        expected_concepts: List[str]
    ) -> SemanticEvaluationResult:
        """
        Performs semantic evaluation of student_answer against reference_answer.
        Maps expected_concepts to student answer segments semantically.
        """
        logger.info(
            "Starting semantic evaluation. Concepts: %s, Student length: %d", 
            expected_concepts, len(student_answer or "")
        )
        
        clean_student = (student_answer or "").strip()
        clean_reference = (reference_answer or "").strip()
        
        # Handle empty/whitespace student answer
        if not clean_student:
            return SemanticEvaluationResult(
                semantic_similarity=0.0,
                semantic_confidence=1.0,
                matched_semantic_concepts=[],
                missing_semantic_concepts=expected_concepts.copy() if expected_concepts else [],
                explanation="Student answer is empty or missing. No semantic match found."
            )

        # Handle empty reference answer
        if not clean_reference:
            return SemanticEvaluationResult(
                semantic_similarity=0.0,
                semantic_confidence=0.5,
                matched_semantic_concepts=[],
                missing_semantic_concepts=[],
                explanation="Reference answer is empty. Semantic evaluation cannot be performed."
            )

        try:
            # 1. Compute overall reference vs student similarity
            ref_emb = self.embedding_service.generate_embedding(clean_reference)
            stud_emb = self.embedding_service.generate_embedding(clean_student)
            
            overall_sim = self.similarity_engine.calculate_similarity(ref_emb, stud_emb)
            
            # 2. Evaluate individual concept matches
            matched_concepts = []
            missing_concepts = []
            
            if expected_concepts:
                # Segment student answer to locate local matches
                stud_segments = self._split_into_segments(clean_student)
                
                if not stud_segments:
                    missing_concepts = expected_concepts.copy()
                else:
                    # Batch generate embeddings for concepts and student segments
                    concept_embs = self.embedding_service.generate_batch_embeddings(expected_concepts)
                    segment_embs = self.embedding_service.generate_batch_embeddings(stud_segments)
                    
                    for idx, concept in enumerate(expected_concepts):
                        concept_emb = concept_embs[idx]
                        max_sim = 0.0
                        
                        for seg_emb in segment_embs:
                            sim = self.similarity_engine.calculate_similarity(concept_emb, seg_emb)
                            if sim > max_sim:
                                max_sim = sim
                                
                        if max_sim >= self.concept_matching_threshold:
                            matched_concepts.append(concept)
                            logger.debug("Concept '%s' matched semantically (max similarity: %.2f)", concept, max_sim)
                        else:
                            missing_concepts.append(concept)
                            logger.debug("Concept '%s' not matched (max similarity: %.2f)", concept, max_sim)
            
            # 3. Determine semantic confidence
            # Lower confidence slightly if answers are extremely short (potential OCR noise/insufficient info)
            semantic_confidence = 0.95
            if len(clean_student) < 10 or len(clean_reference) < 10:
                semantic_confidence = 0.75
                
            # 4. Construct descriptive explanation
            concept_summary = ""
            if expected_concepts:
                concept_summary = (
                    f" Matched concepts: {', '.join(matched_concepts) if matched_concepts else 'None'}."
                    f" Missing concepts: {', '.join(missing_concepts) if missing_concepts else 'None'}."
                )
                
            explanation = (
                f"Semantic similarity with the reference answer is {overall_sim:.2f}."
                f"{concept_summary}"
            )
            
            return SemanticEvaluationResult(
                semantic_similarity=round(overall_sim, 4),
                semantic_confidence=semantic_confidence,
                matched_semantic_concepts=matched_concepts,
                missing_semantic_concepts=missing_concepts,
                explanation=explanation
            )
            
        except Exception as e:
            logger.exception("Exception during semantic evaluation process")
            # Return a safe fallback evaluation result
            return SemanticEvaluationResult(
                semantic_similarity=0.0,
                semantic_confidence=0.0,
                matched_semantic_concepts=[],
                missing_semantic_concepts=expected_concepts.copy() if expected_concepts else [],
                explanation=f"Error performing semantic evaluation: {str(e)}"
            )

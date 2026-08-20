import logging
from typing import Optional, Tuple, List
from AI.schemas.evaluation_schema import QuestionEvaluation

logger = logging.getLogger("GradeMIND.EvidenceFusionEngine")

class EvidenceFusionEngine:
    """
    Fuses multiple independent evaluation signals to determine a final robust score.
    Enforces that LLMs are 'proposal engines' and not the final authority.
    """

    def fuse(
        self,
        llm_eval: Optional[QuestionEvaluation],
        local_score: float,
        max_marks: float,
        concept_coverage: float,
        semantic_similarity: float,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Fuses the LLM's proposed score with deterministic local signals.
        Returns:
            Tuple containing:
            - final_score (float)
            - final_matched_concepts (List[str])
            - final_missing_concepts (List[str])
        """
        if llm_eval is None:
            # If no LLM, the local score is the final authority
            return local_score, [], []

        llm_score = llm_eval.score_awarded
        llm_ratio = (llm_score / max_marks) if max_marks > 0 else 0.0
        local_ratio = (local_score / max_marks) if max_marks > 0 else 0.0

        # Fusion heuristics
        final_score = llm_score

        # Rule 1: High LLM score but poor deterministic evidence -> Penalize
        if llm_ratio > 0.7 and (concept_coverage < 0.4 and semantic_similarity < 0.4):
            logger.warning(
                "FUSION_RULE_TRIGGERED rule=HIGH_LLM_LOW_EVIDENCE "
                f"llm_ratio={llm_ratio:.2f} concept_coverage={concept_coverage:.2f} "
                f"semantic_similarity={semantic_similarity:.2f}"
            )
            # Average the LLM score with the local deterministic score
            final_score = (llm_score + local_score) / 2.0

        # Rule 2: Low LLM score but high deterministic evidence -> Boost
        elif llm_ratio < 0.3 and concept_coverage > 0.8 and semantic_similarity > 0.8:
            logger.warning(
                "FUSION_RULE_TRIGGERED rule=LOW_LLM_HIGH_EVIDENCE "
                f"llm_ratio={llm_ratio:.2f} concept_coverage={concept_coverage:.2f} "
                f"semantic_similarity={semantic_similarity:.2f}"
            )
            # Boost towards the local score
            final_score = (llm_score + local_score) / 2.0

        # Ensure bounds
        final_score = max(0.0, min(final_score, max_marks))
        
        # Round to nearest 0.5
        final_score = round(final_score * 2) / 2

        matched_concepts = llm_eval.matched_keywords or []
        missing_concepts = llm_eval.missing_concepts or []

        logger.info(
            f"FUSION_RESULT llm_score={llm_score} local_score={local_score} "
            f"final_score={final_score} max_marks={max_marks}"
        )

        return final_score, matched_concepts, missing_concepts

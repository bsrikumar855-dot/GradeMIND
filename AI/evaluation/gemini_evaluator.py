"""
Gemini Evaluation Engine.
Secondary evaluator to provide an independent score, confidence, and reasoning.
"""

import logging
import os
from typing import Optional, List, Dict, Any

from AI.schemas.evaluation_schema import GeminiEvaluation, RubricCriterion, ExplainabilityResult
from AI.evaluation.gemini_prompts import GEMINI_EVALUATION_PROMPT
from AI.evaluation.gemini_parser import GeminiParser

logger = logging.getLogger("GradeMIND.GeminiEvaluator")

class GeminiEvaluator:
    """
    Evaluator that calls the Gemini API to produce a secondary evaluation.
    This does NOT replace the primary evaluation pipeline.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash", timeout: int = 15):
        self.model_name = model_name
        self.timeout = timeout
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._client_configured = False
        self._configure_client()

    def _configure_client(self):
        if not self.api_key:
            logger.warning("GEMINI_API_KEY environment variable is not set. Gemini evaluator will be skipped.")
            return
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            # Create the model instance
            # We enforce JSON output using the generation_config if possible, but fallback to prompt instruction
            self.model = genai.GenerativeModel(self.model_name)
            self._client_configured = True
            logger.info(f"Gemini client configured with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            self._client_configured = False

    def evaluate(
        self,
        question: str,
        student_answer: str,
        rubric_points: List[RubricCriterion],
        expected_concepts: List[str],
        max_marks: float,
        concept_coverage_percentage: float = 0.0,
        explainability_result: Optional[ExplainabilityResult] = None
    ) -> Optional[GeminiEvaluation]:
        """
        Evaluate a student's answer using Gemini.
        Returns a GeminiEvaluation object or None if it fails.
        """
        if not self._client_configured:
            logger.warning("Gemini evaluator not configured. Skipping.")
            return None

        if not student_answer or not student_answer.strip():
            logger.info("Empty student answer provided. Skipping Gemini evaluation.")
            return None

        # Prepare inputs
        rubric_text = "\n".join([f"- {p.description} (Marks: {p.allocated_marks})" for p in rubric_points])
        concepts_text = ", ".join(expected_concepts) if expected_concepts else "None specified"
        
        explainability_summary = "None available"
        if explainability_result:
            explainability_summary = f"Evidence Items: {len(explainability_result.evidence)}\n"
            if explainability_result.missing_reasoning:
                explainability_summary += "Missing Details: " + " | ".join(explainability_result.missing_reasoning)

        # Build prompt
        prompt = GEMINI_EVALUATION_PROMPT.format(
            question=question,
            max_marks=max_marks,
            expected_concepts=concepts_text,
            rubric_criteria=rubric_text,
            student_answer=student_answer,
            concept_coverage=concept_coverage_percentage,
            explainability_summary=explainability_summary
        )

        try:
            import google.generativeai as genai
            from google.api_core.exceptions import GoogleAPIError
            
            # Call the API with timeout and retries (handled automatically by the SDK, but we use a short timeout wrapper if needed)
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    temperature=0.1,  # Low temperature for deterministic grading
                    # Using application/json ensures the model tries to return valid JSON
                    response_mime_type="application/json",
                ),
                request_options={"timeout": self.timeout}
            )

            raw_text = response.text
            
            # Parse the response
            return GeminiParser.parse(raw_text, self.model_name)

        except Exception as e:
            logger.error(f"Gemini API evaluation failed: {e}")
            return None

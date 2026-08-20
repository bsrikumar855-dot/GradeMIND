"""
Misconception Engine for GradeMIND.
Identifies recurring errors and synthesizes misconceptions from negative semantic evidence.
"""

import logging
import json
from typing import List, Dict, Tuple, Any
from AI.schemas.evaluation_schema import QuestionEvaluation, Misconception
from AI.evaluation.groq_evaluator import GroqEvaluator

logger = logging.getLogger("GradeMIND.MisconceptionEngine")


class MisconceptionEngine:
    """
    Scans negative evidence across questions to identify and describe recurring misconceptions.
    """
    
    def __init__(self):
        self.llm_evaluator = GroqEvaluator()

    def detect_misconceptions(self, questions: List[QuestionEvaluation]) -> List[Misconception]:
        """
        Groups negative evidence by concept and uses an LLM to synthesize the core misconception.
        """
        # Concept -> List of (Question ID, Evidence Snippet)
        negative_evidence_map: Dict[str, List[Tuple[str, str]]] = {}
        
        for q in questions:
            if not q.semantic_evaluation or not q.semantic_evaluation.evidence:
                continue
                
            for ev in q.semantic_evaluation.evidence:
                if not ev.satisfied and ev.evidence_span and len(ev.evidence_span.strip()) > 5:
                    if ev.criterion not in negative_evidence_map:
                        negative_evidence_map[ev.criterion] = []
                    negative_evidence_map[ev.criterion].append((q.question_number, ev.evidence_span))
                    
        misconceptions = []
        
        for concept, evidence_list in negative_evidence_map.items():
            frequency = len(evidence_list)
            # Only synthesize if there is at least 1 piece of explicit evidence
            if frequency >= 1:
                affected_qs = list(set(q_id for q_id, _ in evidence_list))
                snippets = [span for _, span in evidence_list]
                
                # Synthesize description using LLM
                description = self._synthesize_misconception(concept, snippets)
                
                if description:
                    misconceptions.append(
                        Misconception(
                            concept=concept,
                            description=description,
                            frequency=frequency,
                            affected_questions=affected_qs,
                            evidence=snippets
                        )
                    )
                    
        return misconceptions
        
    def _synthesize_misconception(self, concept: str, evidence_snippets: List[str]) -> str:
        """
        Calls the LLM to identify the core misunderstanding from raw evidence.
        """
        if not self.llm_evaluator.is_available():
            # Fallback if LLM is unavailable
            return f"Struggles with the concept: {concept}"
            
        system_prompt = (
            "You are an expert educator diagnosing student misconceptions.\n"
            "You are given a core concept that the student failed to demonstrate, along with snippets of their incorrect answers.\n"
            "Identify the specific cognitive error or misconception they are making in 1 short, actionable sentence.\n"
            "Example: 'Confuses force with acceleration.' or 'Fails to account for air resistance.'\n"
            "Do not use generic phrases like 'The student misunderstood...'. Get straight to the point."
        )
        
        evidence_text = "\n".join(f"- {e}" for e in evidence_snippets)
        user_prompt = f"Concept: {concept}\nStudent Evidence:\n{evidence_text}"
        
        import requests
        from AI.evaluation.groq_evaluator import GROQ_API_URL
        
        headers = {
            "Authorization": f"Bearer {self.llm_evaluator.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_evaluator.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 100
        }
        
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            # Remove any wrapping quotes if present
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            return content
        except Exception as exc:
            logger.warning("Failed to synthesize misconception for '%s': %s", concept, exc)
            return f"Struggles with the concept: {concept}"

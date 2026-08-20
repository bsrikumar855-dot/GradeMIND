"""
Recommendation Engine for GradeMIND.
Generates structured, evidence-backed study recommendations based on weak concepts and misconceptions.
"""

import logging
import json
from typing import List, Dict
from AI.schemas.evaluation_schema import TopicMastery, KnowledgeGap, ConceptMastery, Misconception, Recommendation
from AI.evaluation.groq_evaluator import GroqEvaluator

logger = logging.getLogger("GradeMIND.RecommendationEngine")


class RecommendationEngine:
    """
    Formulates educational study recommendations from curriculum performance.
    """
    def __init__(self):
        self.llm_evaluator = GroqEvaluator()

    def generate_recommendations(
        self, 
        concept_mastery: Dict[str, ConceptMastery], 
        misconceptions: List[Misconception]
    ) -> List[Recommendation]:
        """
        Creates actionable, structured recommendations mapped directly to weaknesses.
        """
        recommendations = []
        
        # 1. Identify weak concepts from ConceptMastery
        weak_concepts = [c for c, m in concept_mastery.items() if m.status in ("WEAK", "CRITICAL")]
        
        # 2. Combine with concepts that have active misconceptions
        misconception_concepts = [m.concept for m in misconceptions]
        
        target_concepts = list(set(weak_concepts + misconception_concepts))
        
        if not target_concepts:
            return recommendations
            
        # We process up to 3 most critical concepts to avoid overwhelming the student
        target_concepts = target_concepts[:3]
        
        if not self.llm_evaluator.is_available():
            for concept in target_concepts:
                recommendations.append(Recommendation(
                    weak_concept=concept,
                    recommended_actions=[f"Review foundational principles of {concept}", "Practice related exercises"]
                ))
            return recommendations
            
        # 3. Generate detailed actions using LLM
        for concept in target_concepts:
            # Find any related misconception to guide the recommendation
            related_misc = next((m for m in misconceptions if m.concept == concept), None)
            
            system_prompt = (
                "You are an expert tutor giving a student targeted study recommendations.\n"
                "You will be given a weak concept. Generate exactly 3 specific, actionable sub-topics or review actions to improve.\n"
                "Respond ONLY with a JSON array of strings. Do not include any other text."
            )
            
            user_prompt = f"Weak concept: {concept}\n"
            if related_misc:
                user_prompt += f"Known Misconception to correct: {related_misc.description}\n"
                
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
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            
            # Since response_format json_object is used, we wrap the prompt slightly
            payload["messages"][0]["content"] = system_prompt.replace(
                "Respond ONLY with a JSON array of strings",
                "Respond ONLY with a JSON object containing an 'actions' array of strings"
            )
            
            try:
                resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                actions = parsed.get("actions", [])
                
                if actions:
                    recommendations.append(Recommendation(
                        weak_concept=concept,
                        recommended_actions=actions
                    ))
            except Exception as exc:
                logger.warning("Failed to generate recommendation for '%s': %s", concept, exc)
                recommendations.append(Recommendation(
                    weak_concept=concept,
                    recommended_actions=[f"Review core components of {concept}"]
                ))
                
        return recommendations

"""
Recommendation Engine for GradeMIND.
Generates student-focused study recommendations based on mastery results and knowledge gaps.
"""

import logging
from typing import List, Dict
from AI.schemas.evaluation_schema import TopicMastery, KnowledgeGap

logger = logging.getLogger("GradeMIND.RecommendationEngine")


class RecommendationEngine:
    """
    Formulates educational study recommendations from curriculum performance.
    """

    def generate_recommendations(
        self, 
        mastery_results: Dict[str, TopicMastery], 
        gaps: List[KnowledgeGap]
    ) -> List[str]:
        """
        Creates actionable study recommendations based on weak/critical topics and knowledge gaps.
        """
        recommendations = []

        # 1. Identify weak/critical topics
        weak_topics = []
        critical_topics = []
        developing_topics = []

        for topic, result in mastery_results.items():
            if result.status == "CRITICAL":
                critical_topics.append(topic)
            elif result.status == "WEAK":
                weak_topics.append(topic)
            elif result.status == "DEVELOPING":
                developing_topics.append(topic)

        # 2. Add topic-level study recommendations
        for topic in critical_topics:
            recommendations.append(f"Prioritize re-learning the core components of '{topic}' as performance is critical.")
        
        for topic in weak_topics:
            recommendations.append(f"Review and practice questions under the topic '{topic}' to build foundation.")

        for topic in developing_topics:
            recommendations.append(f"Reinforce your understanding of '{topic}' with target exercises to achieve full mastery.")

        # 3. Add concept-level study recommendations from knowledge gaps
        for gap in gaps:
            if gap.severity == "HIGH":
                missing_str = ", ".join(gap.missing_concepts[:3])
                recommendations.append(f"Focus on key missing concepts in '{gap.topic}': {missing_str}.")
            elif gap.severity == "MEDIUM":
                missing_str = ", ".join(gap.missing_concepts[:2])
                recommendations.append(f"Study specific details of {missing_str} in '{gap.topic}'.")

        # 4. Fallback if student did exceptionally well
        if not recommendations:
            recommendations.append("Excellent work! Review advanced materials or explore topics beyond this curriculum to expand knowledge.")

        # Return unique recommendations up to a limit (e.g. 5)
        return list(dict.fromkeys(recommendations))[:5]

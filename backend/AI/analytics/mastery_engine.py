"""
Mastery Engine for GradeMIND.
Evaluates student topic mastery based on question-level evaluations.
"""

import logging
from typing import List, Dict, Tuple
from AI.schemas.evaluation_schema import QuestionEvaluation, TopicMastery

logger = logging.getLogger("GradeMIND.MasteryEngine")


class MasteryEngine:
    """
    Evaluates student performance to determine topic-level mastery.
    """

    def _extract_topic_name(self, q: QuestionEvaluation) -> str:
        """
        Extracts a clean topic name from question curriculum context,
        falling back to default values if missing.
        """
        if q.curriculum_context and q.curriculum_context.topic:
            # Topic format is usually "TopicName. Objectives: ..."
            parts = q.curriculum_context.topic.split(". Objectives:")
            if parts:
                return parts[0].strip()
        return "General Topic"

    def evaluate_mastery(self, questions: List[QuestionEvaluation]) -> Dict[str, TopicMastery]:
        """
        Groups questions by topic, aggregates scores, and determines mastery level.
        """
        if not questions:
            return {}

        # Group by topic: topic -> (total_awarded, total_max, total_confidence, count)
        topic_groups: Dict[str, Tuple[float, float, float, int]] = {}

        for q in questions:
            topic = self._extract_topic_name(q)
            score = q.score_awarded
            max_marks = q.max_marks
            conf = q.confidence

            if topic not in topic_groups:
                topic_groups[topic] = (score, max_marks, conf, 1)
            else:
                s, m, c, count = topic_groups[topic]
                topic_groups[topic] = (s + score, m + max_marks, c + conf, count + 1)

        mastery_results = {}
        for topic, (awarded, max_m, conf_sum, count) in topic_groups.items():
            # Calculate mastery score
            mastery_score = (awarded / max_m) if max_m > 0.0 else 0.0
            mastery_score = round(min(1.0, max(0.0, mastery_score)), 4)
            
            # Average confidence
            avg_conf = round(conf_sum / count, 4)

            # Determine status based on boundaries
            if mastery_score >= 0.80:
                status = "MASTERED"
            elif mastery_score >= 0.50:
                status = "DEVELOPING"
            elif mastery_score >= 0.30:
                status = "WEAK"
            else:
                status = "CRITICAL"

            mastery_results[topic] = TopicMastery(
                topic=topic,
                mastery_score=mastery_score,
                confidence=avg_conf,
                status=status
            )
            
        return mastery_results

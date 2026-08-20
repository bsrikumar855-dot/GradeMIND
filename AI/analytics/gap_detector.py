"""
Gap Detector for GradeMIND.
Analyzes missing concepts to isolate student learning gaps and severities.
"""

import logging
from typing import List, Dict, Set, Tuple
from AI.schemas.evaluation_schema import QuestionEvaluation, KnowledgeGap

logger = logging.getLogger("GradeMIND.GapDetector")


class GapDetector:
    """
    Scans evaluations for missing concepts and computes topic gap severities.
    """

    def _extract_topic_name(self, q: QuestionEvaluation) -> str:
        if q.curriculum_context and q.curriculum_context.topic:
            parts = q.curriculum_context.topic.split(". Objectives:")
            if parts:
                return parts[0].strip()
        return "General Topic"

    def detect_gaps(self, questions: List[QuestionEvaluation]) -> List[KnowledgeGap]:
        """
        Extracts missing concepts per topic and assigns severity (LOW, MEDIUM, HIGH).
        """
        if not questions:
            return []

        # Map to hold missing concepts per topic
        # topic -> (set of missing concepts, set of total expected/seeded concepts)
        topic_gaps: Dict[str, Tuple[Set[str], Set[str]]] = {}

        for q in questions:
            topic = self._extract_topic_name(q)
            
            # Extract missing concepts from semantic evaluation or legacy fields
            missing = set()
            expected = set()

            # Read from semantic engine if available (prioritized)
            if q.semantic_evaluation:
                for ev in q.semantic_evaluation.evidence:
                    if not ev.satisfied:
                        missing.add(ev.criterion)
                    expected.add(ev.criterion)
            else:
                missing.update(q.missing_concepts)
                # Fallback to matched + missing keywords
                matched = q.matched_keywords or []
                expected.update(matched)
                expected.update(q.missing_concepts)

            if topic not in topic_gaps:
                topic_gaps[topic] = (missing, expected)
            else:
                m_set, e_set = topic_gaps[topic]
                m_set.update(missing)
                e_set.update(expected)

        gaps = []
        for topic, (missing_set, expected_set) in topic_gaps.items():
            if not missing_set:
                continue

            # Determine severity based on ratio of missing concepts to total expected
            total_count = len(expected_set)
            missing_count = len(missing_set)
            
            ratio = (missing_count / total_count) if total_count > 0 else 0.0

            if ratio >= 0.60:
                severity = "HIGH"
            elif ratio >= 0.30:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            gaps.append(
                KnowledgeGap(
                    topic=topic,
                    missing_concepts=list(missing_set),
                    severity=severity
                )
            )

        return gaps

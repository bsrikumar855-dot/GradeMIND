"""
Learning Analytics Service for GradeMIND.
Provides unified intelligence API to evaluate student topic masteries, gaps, and study tasks.
"""

import logging
from typing import List, Union, Dict, Any
from AI.schemas.evaluation_schema import (
    SubmissionEvaluation, QuestionEvaluation, LearningAnalyticsResult, TopicMastery, KnowledgeGap
)
from AI.analytics.mastery_engine import MasteryEngine
from AI.analytics.gap_detector import GapDetector
from AI.analytics.recommendation_engine import RecommendationEngine

logger = logging.getLogger("GradeMIND.LearningAnalyticsService")


class LearningAnalyticsService:
    """
    Main service entrypoint for compiling student learning analytics indicators.
    """

    def __init__(self):
        self.mastery_engine = MasteryEngine()
        self.gap_detector = GapDetector()
        self.recommendation_engine = RecommendationEngine()

    def _ensure_pydantic_questions(
        self, 
        questions: Union[List[QuestionEvaluation], List[Dict[str, Any]]]
    ) -> List[QuestionEvaluation]:
        """
        Converts lists of dict questions into proper QuestionEvaluation models if necessary.
        """
        parsed = []
        for q in questions:
            if isinstance(q, dict):
                parsed.append(QuestionEvaluation.model_validate(q))
            else:
                parsed.append(q)
        return parsed

    def analyze_submission(
        self, 
        submission: Union[SubmissionEvaluation, Dict[str, Any]]
    ) -> LearningAnalyticsResult:
        """
        Parses a single exam submission and runs analysis models to generate learning analytics.
        """
        logger.info("Running learning analytics for submission...")
        
        # Resolve questions list
        if isinstance(submission, dict):
            raw_questions = submission.get("questions", [])
        else:
            raw_questions = submission.questions

        questions = self._ensure_pydantic_questions(raw_questions)

        if not questions:
            return LearningAnalyticsResult(overall_mastery=0.0)

        # 1. Run Mastery Engine
        mastery_results = self.mastery_engine.evaluate_mastery(questions)

        # 2. Run Gap Detector
        gaps = self.gap_detector.detect_gaps(questions)

        # 3. Run Recommendation Engine
        recommendations = self.recommendation_engine.generate_recommendations(mastery_results, gaps)

        # 4. Extract mastered vs weak topics
        mastered_topics = []
        weak_topics = []
        mastery_scores = []

        for topic, result in mastery_results.items():
            mastery_scores.append(result.mastery_score)
            if result.status == "MASTERED":
                mastered_topics.append(topic)
            elif result.status in ("WEAK", "CRITICAL"):
                weak_topics.append(topic)

        # 5. Compute overall mastery average
        overall_mastery = (sum(mastery_scores) / len(mastery_scores)) if mastery_scores else 0.0
        overall_mastery = round(overall_mastery, 4)

        return LearningAnalyticsResult(
            mastered_topics=mastered_topics,
            weak_topics=weak_topics,
            knowledge_gaps=gaps,
            recommendations=recommendations,
            overall_mastery=overall_mastery
        )

    def analyze_student_history(
        self, 
        submissions: List[Union[SubmissionEvaluation, Dict[str, Any]]]
    ) -> LearningAnalyticsResult:
        """
        Aggregates multiple submissions from a student's history to build a longitudinal analytics profile.
        """
        logger.info("Running learning analytics across student history (%d submissions)...", len(submissions))
        
        # Combine all questions from all submissions
        all_questions = []
        for sub in submissions:
            if isinstance(sub, dict):
                raw_qs = sub.get("questions", [])
            else:
                raw_qs = sub.questions
            all_questions.extend(self._ensure_pydantic_questions(raw_qs))

        if not all_questions:
            return LearningAnalyticsResult(overall_mastery=0.0)

        # Perform the same analytics pipeline over aggregate questions dataset
        mastery_results = self.mastery_engine.evaluate_mastery(all_questions)
        gaps = self.gap_detector.detect_gaps(all_questions)
        recommendations = self.recommendation_engine.generate_recommendations(mastery_results, gaps)

        mastered_topics = []
        weak_topics = []
        mastery_scores = []

        for topic, result in mastery_results.items():
            mastery_scores.append(result.mastery_score)
            if result.status == "MASTERED":
                mastered_topics.append(topic)
            elif result.status in ("WEAK", "CRITICAL"):
                weak_topics.append(topic)

        overall_mastery = (sum(mastery_scores) / len(mastery_scores)) if mastery_scores else 0.0
        overall_mastery = round(overall_mastery, 4)

        return LearningAnalyticsResult(
            mastered_topics=mastered_topics,
            weak_topics=weak_topics,
            knowledge_gaps=gaps,
            recommendations=recommendations,
            overall_mastery=overall_mastery
        )

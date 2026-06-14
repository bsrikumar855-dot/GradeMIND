"""
GradeMIND Dashboard Service.
Provides analytical insights, overview metrics, score distributions, and monitoring statistics.
"""

import os
import json
import logging
from uuid import UUID
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus

logger = logging.getLogger("GradeMIND.DashboardService")


class DashboardService:
    """
    Service layer orchestrating metrics gathering and formatting for the Teacher Dashboard.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_overview_metrics(self, user_id: Optional[UUID], is_admin: bool = False) -> Dict[str, Any]:
        """
        Gathers aggregate overview statistics for the current user's exams.
        """
        try:
            exam_query = self.db.query(Exam)
            if not is_admin:
                exam_query = exam_query.filter(Exam.teacher_id == user_id)
            exams = exam_query.all()
            exam_ids = [e.id for e in exams]

            total_exams = len(exam_ids)
            if total_exams == 0:
                return {
                    "total_exams": 0,
                    "total_submissions": 0,
                    "evaluated_submissions": 0,
                    "average_score": 0.0,
                    "average_confidence": 0.0,
                    "published_exams_count": 0,
                    "unpublished_exams_count": 0,
                    "average_student_score": 0.0,
                    "result_publication_rate": 0.0,
                    "autonomous_evaluations": 0,
                    "answer_key_evaluations": 0
                }

            # Gather submission counts
            submissions_query = self.db.query(Submission).filter(Submission.exam_id.in_(exam_ids))
            total_submissions = submissions_query.count()

            # Completed submissions
            evaluated_subs = submissions_query.filter(Submission.status == SubmissionStatus.COMPLETED).all()
            evaluated_count = len(evaluated_subs)

            if evaluated_count > 0:
                scores = [s.obtained_marks for s in evaluated_subs if s.obtained_marks is not None]
                avg_score = sum(scores) / len(scores) if scores else 0.0
                
                confidences = [s.evaluation_confidence for s in evaluated_subs if s.evaluation_confidence is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            else:
                avg_score = 0.0
                avg_confidence = 0.0

            # Calculate new fields
            published_exams_count = sum(1 for e in exams if getattr(e, "results_published", False))
            unpublished_exams_count = total_exams - published_exams_count
            result_publication_rate = (published_exams_count / total_exams) * 100.0 if total_exams > 0 else 0.0
            mode_counts = self._evaluation_mode_counts(evaluated_subs)

            return {
                "total_exams": total_exams,
                "total_submissions": total_submissions,
                "evaluated_submissions": evaluated_count,
                "average_score": round(avg_score, 2),
                "average_confidence": round(avg_confidence, 4),
                "published_exams_count": published_exams_count,
                "unpublished_exams_count": unpublished_exams_count,
                "average_student_score": round(avg_score, 2),
                "result_publication_rate": round(result_publication_rate, 2),
                "autonomous_evaluations": mode_counts["AI_AUTONOMOUS"],
                "answer_key_evaluations": mode_counts["ANSWER_KEY"]
            }
        except Exception as e:
            logger.error(f"Error gathering overview metrics: {e}")
            return {
                "total_exams": 0,
                "total_submissions": 0,
                "evaluated_submissions": 0,
                "average_score": 0.0,
                "average_confidence": 0.0,
                "published_exams_count": 0,
                "unpublished_exams_count": 0,
                "average_student_score": 0.0,
                "result_publication_rate": 0.0,
                "autonomous_evaluations": 0,
                "answer_key_evaluations": 0
            }

    def get_exam_analytics(self, exam_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Compiles performance metrics for a specific exam.
        """
        try:
            exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
            if not exam:
                return None

            subs = self.db.query(Submission).filter(Submission.exam_id == exam_id).all()
            submission_count = len(subs)

            completed_subs = [s for s in subs if s.status == SubmissionStatus.COMPLETED]
            completed_count = len(completed_subs)

            if completed_count > 0:
                scores = [s.obtained_marks for s in completed_subs if s.obtained_marks is not None]
                if scores:
                    average_score = sum(scores) / len(scores)
                    top_score = max(scores)
                    lowest_score = min(scores)
                else:
                    average_score = 0.0
                    top_score = 0.0
                    lowest_score = 0.0
            else:
                average_score = 0.0
                top_score = 0.0
                lowest_score = 0.0

            completion_rate = (completed_count / submission_count * 100.0) if submission_count > 0 else 0.0

            return {
                "exam_id": str(exam.id),
                "title": exam.title,
                "submission_count": submission_count,
                "average_score": round(average_score, 2),
                "top_score": top_score,
                "lowest_score": lowest_score,
                "completion_rate": round(completion_rate, 2)
            }
        except Exception as e:
            logger.error(f"Error compiling exam analytics: {e}")
            return None

    def get_submission_review(self, submission_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed question breakdown, feedback, and fairness checks for review.
        """
        try:
            submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
            if not submission:
                return None

            question_breakdown = []
            feedback = {
                "strengths": [],
                "weaknesses": [],
                "improvements": [],
                "summary": ""
            }
            fairness_checks = []

            # Attempt to read detailed JSON evaluation outputs
            if submission.evaluation_output_path and os.path.exists(submission.evaluation_output_path):
                try:
                    with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
                        eval_data = json.load(f)

                    # Build breakdown
                    for q in eval_data.get("questions", []):
                        question_breakdown.append({
                            "question_number": str(q.get("question_number")),
                            "max_marks": q.get("max_marks"),
                            "score_awarded": q.get("score_awarded"),
                            "student_answer_extracted": q.get("student_answer_extracted"),
                            "criteria_feedback": q.get("criteria_feedback"),
                            "confidence": q.get("confidence"),
                            "concept_coverage": q.get("concept_coverage"),
                            "evaluation_mode": q.get("evaluation_mode") or eval_data.get("evaluation_mode")
                        })

                    # Build feedback
                    feedback = {
                        "strengths": eval_data.get("strengths", []),
                        "weaknesses": eval_data.get("weaknesses", []),
                        "improvements": eval_data.get("improvements", []),
                        "summary": eval_data.get("summary", "")
                    }

                    # Build fairness check
                    fairness_checks.append({
                        "metric": "neutrality_score",
                        "value": eval_data.get("fairness_score", 1.0),
                        "status": "PASSED" if eval_data.get("fairness_verified", True) else "FLAGGED"
                    })
                except Exception as e:
                    logger.warning(f"Could not load evaluation data from {submission.evaluation_output_path}: {e}")

            return {
                "student": submission.student_name,
                "score": submission.obtained_marks or 0.0,
                "confidence": submission.evaluation_confidence or 0.0,
                "question_breakdown": question_breakdown,
                "feedback": feedback,
                "fairness_checks": fairness_checks
            }
        except Exception as e:
            logger.error(f"Error retrieving submission review: {e}")
            return None

    def get_monitoring_data(self, user_id: Optional[UUID], is_admin: bool = False) -> Dict[str, Any]:
        """
        Compiles aggregate evaluation monitoring data including score and confidence distributions.
        """
        try:
            exam_query = self.db.query(Exam)
            if not is_admin:
                exam_query = exam_query.filter(Exam.teacher_id == user_id)
            exams = exam_query.all()
            exam_ids = [e.id for e in exams]

            if not exam_ids:
                return self._empty_monitoring_payload()

            subs = self.db.query(Submission).filter(Submission.exam_id.in_(exam_ids)).all()
            total_submissions = len(subs)

            completed_subs = [s for s in subs if s.status == SubmissionStatus.COMPLETED]
            completed_count = len(completed_subs)
            failed_count = sum(1 for s in subs if s.status == SubmissionStatus.FAILED)

            if completed_count > 0:
                scores = [s.obtained_marks for s in completed_subs if s.obtained_marks is not None]
                avg_score = sum(scores) / len(scores) if scores else 0.0

                confidences = [s.evaluation_confidence for s in completed_subs if s.evaluation_confidence is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            else:
                avg_score = 0.0
                avg_confidence = 0.0

            # Score Distribution (percentage brackets)
            score_dist = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "below_60": 0}
            # Confidence Distribution
            conf_dist = {"high_confidence_85_plus": 0, "medium_confidence_70_84": 0, "low_confidence_below_70": 0}

            # Fairness Metrics
            fairness_scores = []
            flagged_count = 0

            for s in completed_subs:
                # Score grouping
                if s.obtained_marks is not None and s.total_marks and s.total_marks > 0:
                    pct = (s.obtained_marks / s.total_marks) * 100.0
                    if pct >= 90.0:
                        score_dist["90-100"] += 1
                    elif pct >= 80.0:
                        score_dist["80-89"] += 1
                    elif pct >= 70.0:
                        score_dist["70-79"] += 1
                    elif pct >= 60.0:
                        score_dist["60-69"] += 1
                    else:
                        score_dist["below_60"] += 1
                else:
                    score_dist["below_60"] += 1

                # Confidence grouping
                conf = s.evaluation_confidence or 0.0
                if conf >= 0.85:
                    conf_dist["high_confidence_85_plus"] += 1
                elif conf >= 0.70:
                    conf_dist["medium_confidence_70_84"] += 1
                else:
                    conf_dist["low_confidence_below_70"] += 1

                # Try parsing fairness details
                if s.evaluation_output_path and os.path.exists(s.evaluation_output_path):
                    try:
                        with open(s.evaluation_output_path, "r", encoding="utf-8") as f:
                            eval_data = json.load(f)
                            f_score = eval_data.get("fairness_score", 1.0)
                            f_verified = eval_data.get("fairness_verified", True)
                            fairness_scores.append(f_score)
                            if not f_verified:
                                flagged_count += 1
                    except Exception:
                        pass

            avg_fairness = sum(fairness_scores) / len(fairness_scores) if fairness_scores else 1.0
            bias_free_rate = ((completed_count - flagged_count) / completed_count * 100.0) if completed_count > 0 else 100.0
            mode_counts = self._evaluation_mode_counts(completed_subs)

            return {
                "aggregate_analytics": {
                    "total_submissions": total_submissions,
                    "completed_submissions": completed_count,
                    "failed_submissions": failed_count,
                    "average_score": round(avg_score, 2),
                    "average_confidence": round(avg_confidence, 4),
                    "autonomous_evaluations": mode_counts["AI_AUTONOMOUS"],
                    "answer_key_evaluations": mode_counts["ANSWER_KEY"]
                },
                "score_distribution": score_dist,
                "confidence_distribution": conf_dist,
                "fairness_metrics": {
                    "average_fairness_score": round(avg_fairness, 2),
                    "bias_free_rate": round(bias_free_rate, 2),
                    "flagged_submissions_count": flagged_count
                }
            }
        except Exception as e:
            logger.error(f"Error gathering monitoring data: {e}")
            return self._empty_monitoring_payload()

    def _empty_monitoring_payload(self) -> Dict[str, Any]:
        return {
            "aggregate_analytics": {
                "total_submissions": 0,
                "completed_submissions": 0,
                "failed_submissions": 0,
                "average_score": 0.0,
                "average_confidence": 0.0,
                "autonomous_evaluations": 0,
                "answer_key_evaluations": 0
            },
            "score_distribution": {
                "90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "below_60": 0
            },
            "confidence_distribution": {
                "high_confidence_85_plus": 0,
                "medium_confidence_70_84": 0,
                "low_confidence_below_70": 0
            },
            "fairness_metrics": {
                "average_fairness_score": 1.0,
                "bias_free_rate": 100.0,
                "flagged_submissions_count": 0
            }
        }

    def _evaluation_mode_counts(self, submissions: List[Submission]) -> Dict[str, int]:
        counts = {"AI_AUTONOMOUS": 0, "ANSWER_KEY": 0}
        for submission in submissions:
            mode = None
            if submission.evaluation_output_path and os.path.exists(submission.evaluation_output_path):
                try:
                    with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
                        mode = json.load(f).get("evaluation_mode")
                except Exception:
                    mode = None
            if not mode and getattr(submission, "exam", None):
                mode = getattr(submission.exam, "evaluation_mode", None)
            if mode not in counts:
                mode = "ANSWER_KEY" if getattr(submission.exam, "answer_key_url", None) else "AI_AUTONOMOUS"
            counts[mode] += 1
        return counts

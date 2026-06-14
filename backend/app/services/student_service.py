"""
GradeMIND Student Portal Service.
Manages student results aggregation, detailed review queries, and enforces result publication and ownership rules.
"""

import os
import json
import logging
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus

logger = logging.getLogger("GradeMIND.StudentService")


class StudentService:
    """
    Service layer for student-specific queries and access control validation.
    """

    def __init__(self, db: Session):
        self.db = db

    def publish_exam_results(self, exam_id: UUID) -> Optional[Exam]:
        """
        Marks an exam's results as published.
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            return None
        exam.results_published = True
        exam.published_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(exam)
        logger.info(f"Published results for exam {exam_id}")
        return exam

    def unpublish_exam_results(self, exam_id: UUID) -> Optional[Exam]:
        """
        Unpublishes an exam's results.
        """
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            return None
        exam.results_published = False
        exam.published_at = None
        self.db.commit()
        self.db.refresh(exam)
        logger.info(f"Unpublished results for exam {exam_id}")
        return exam

    def get_student_results_overview(self, student_name: str) -> Dict[str, Any]:
        """
        Aggregates results for a specific student across all published exams.
        """
        # Join Submission with Exam to filter on results_published
        subs = (
            self.db.query(Submission)
            .join(Exam, Submission.exam_id == Exam.id)
            .filter(
                Exam.results_published == True,
                Submission.student_name.ilike(student_name)
            )
            .all()
        )

        completed_subs = [s for s in subs if s.status == SubmissionStatus.COMPLETED]
        
        if completed_subs:
            scores = [s.obtained_marks for s in completed_subs if s.obtained_marks is not None]
            avg_score = sum(scores) / len(scores) if scores else 0.0
        else:
            avg_score = 0.0

        reports_list = []
        for s in subs:
            # Fetch Exam title
            exam = self.db.query(Exam).filter(Exam.id == s.exam_id).first()
            exam_title = exam.title if exam else "Unknown Exam"
            
            reports_list.append({
                "submission_id": str(s.id),
                "exam_id": str(s.exam_id),
                "exam_title": exam_title,
                "obtained_marks": s.obtained_marks,
                "total_marks": s.total_marks,
                "status": s.status,
                "created_at": s.created_at
            })

        return {
            "student_id": student_name,
            "total_exams": len(subs),
            "average_score": round(avg_score, 2),
            "reports": reports_list
        }

    def verify_access_and_get_submission(self, submission_id: UUID, current_user: dict) -> Submission:
        """
        Retrieves a submission and verifies if the current user has access to it.
        Raises ValueError with an error code/message for unauthorized attempts.
        """
        submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError("SUBMISSION_NOT_FOUND")

        exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if not exam:
            raise ValueError("EXAM_NOT_FOUND")

        role = current_user.get("role")
        user_name = current_user.get("name")

        # Teachers and Admins bypass ownership and publication rules
        if role in ["TEACHER", "ADMIN"]:
            return submission

        # Student rules:
        # 1. Must own the submission
        if not submission.student_name.lower() == user_name.lower():
            raise ValueError("ACCESS_DENIED")

        # 2. Results must be published
        if not exam.results_published:
            raise ValueError("RESULTS_UNPUBLISHED")

        return submission

    def get_student_submission_review(self, submission: Submission) -> Dict[str, Any]:
        """
        Compiles the detailed review breakdown for a verified submission.
        """
        exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()
        exam_title = exam.title if exam else "Unknown Exam"

        question_breakdown = []
        feedback = {
            "strengths": [],
            "weaknesses": [],
            "improvements": [],
            "summary": ""
        }

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
                    "study_recommendations": eval_data.get("study_recommendations", []),
                    "summary": eval_data.get("summary", "")
                }
            except Exception as e:
                logger.warning(f"Could not load evaluation data from {submission.evaluation_output_path}: {e}")

        return {
            "submission_id": str(submission.id),
            "exam_title": exam_title,
            "score": submission.obtained_marks or 0.0,
            "confidence": submission.evaluation_confidence or 0.0,
            "feedback": feedback,
            "question_breakdown": question_breakdown
        }

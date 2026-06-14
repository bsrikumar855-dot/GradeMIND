"""
GradeMIND Submission Repository.
Data access layer for the Submission model. Handles all direct database operations
following the repository pattern established by UserRepository.
"""

from typing import Optional, List
from uuid import UUID
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.submission import Submission

logger = logging.getLogger("GradeMIND.SubmissionRepository")


class SubmissionRepository:
    """Repository class encapsulating all Submission database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_submission(self, submission: Submission) -> Submission:
        """
        Persist a new submission record to the database.

        Args:
            submission: Populated Submission model instance.

        Returns:
            The created Submission with database-generated fields populated.

        Raises:
            SQLAlchemyError: On database constraint violations or connection errors.
        """
        try:
            self.session.add(submission)
            self.session.commit()
            self.session.refresh(submission)
            logger.info(
                "DB_STAGE submission_created submission_id=%s status=%s",
                submission.id,
                submission.status,
            )
            return submission
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get_submission(self, submission_id: UUID) -> Optional[Submission]:
        """
        Retrieve a single submission by its primary key.

        Args:
            submission_id: UUID of the submission.

        Returns:
            Submission instance or None if not found.
        """
        return self.session.query(Submission).filter(
            Submission.id == submission_id
        ).first()

    def list_submissions(
        self,
        exam_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Submission]:
        """
        List submissions with optional filtering by exam and status.

        Args:
            exam_id: Filter by specific exam.
            status: Filter by submission status.
            skip: Pagination offset.
            limit: Maximum number of records to return.

        Returns:
            List of Submission instances matching the filters.
        """
        query = self.session.query(Submission)

        if exam_id is not None:
            query = query.filter(Submission.exam_id == exam_id)
        if status is not None:
            query = query.filter(Submission.status == status)

        query = query.order_by(Submission.created_at.desc())
        return query.offset(skip).limit(limit).all()

    def count_submissions(
        self,
        exam_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count submissions matching the given filters.

        Args:
            exam_id: Filter by specific exam.
            status: Filter by submission status.

        Returns:
            Integer count of matching records.
        """
        query = self.session.query(Submission)

        if exam_id is not None:
            query = query.filter(Submission.exam_id == exam_id)
        if status is not None:
            query = query.filter(Submission.status == status)

        return query.count()

    def update_status(
        self,
        submission_id: UUID,
        status: str,
        ocr_status: Optional[str] = None,
        evaluation_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Submission]:
        """
        Update the processing status fields of a submission.

        Args:
            submission_id: UUID of the submission to update.
            status: New overall status value.
            ocr_status: New OCR pipeline status.
            evaluation_status: New evaluation pipeline status.
            error_message: Error description if the pipeline failed.

        Returns:
            Updated Submission or None if not found.
        """
        submission = self.get_submission(submission_id)
        if not submission:
            return None

        try:
            submission.status = status
            if ocr_status is not None:
                submission.ocr_status = ocr_status
            if evaluation_status is not None:
                submission.evaluation_status = evaluation_status
            if error_message is not None:
                submission.error_message = error_message

            self.session.commit()
            self.session.refresh(submission)
            logger.info(
                "DB_STAGE status_updated submission_id=%s status=%s ocr_status=%s evaluation_status=%s error=%s",
                submission_id,
                submission.status,
                submission.ocr_status,
                submission.evaluation_status,
                submission.error_message,
            )
            return submission
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def update_results(
        self,
        submission_id: UUID,
        obtained_marks: Optional[float] = None,
        total_marks: Optional[float] = None,
        ocr_confidence: Optional[float] = None,
        evaluation_confidence: Optional[float] = None,
        ocr_output_path: Optional[str] = None,
        evaluation_output_path: Optional[str] = None,
        report_path: Optional[str] = None
    ) -> Optional[Submission]:
        """
        Update result fields after OCR or evaluation processing completes.

        Args:
            submission_id: UUID of the submission to update.
            obtained_marks: Marks awarded by the evaluation engine.
            total_marks: Maximum possible marks.
            ocr_confidence: Confidence score from OCR processing.
            evaluation_confidence: Confidence score from evaluation.
            ocr_output_path: Path to the stored OCR output JSON.
            evaluation_output_path: Path to the stored evaluation output JSON.
            report_path: Path to the generated report file.

        Returns:
            Updated Submission or None if not found.
        """
        submission = self.get_submission(submission_id)
        if not submission:
            return None

        try:
            if obtained_marks is not None:
                submission.obtained_marks = obtained_marks
            if total_marks is not None:
                submission.total_marks = total_marks
            if ocr_confidence is not None:
                submission.ocr_confidence = ocr_confidence
            if evaluation_confidence is not None:
                submission.evaluation_confidence = evaluation_confidence
            if ocr_output_path is not None:
                submission.ocr_output_path = ocr_output_path
            if evaluation_output_path is not None:
                submission.evaluation_output_path = evaluation_output_path
            if report_path is not None:
                submission.report_path = report_path

            self.session.commit()
            self.session.refresh(submission)
            logger.info(
                "DB_STAGE results_updated submission_id=%s obtained_marks=%s total_marks=%s ocr_confidence=%s evaluation_confidence=%s ocr_output_path=%s evaluation_output_path=%s report_path=%s",
                submission_id,
                submission.obtained_marks,
                submission.total_marks,
                submission.ocr_confidence,
                submission.evaluation_confidence,
                submission.ocr_output_path,
                submission.evaluation_output_path,
                submission.report_path,
            )
            return submission
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete_submission(self, submission_id: UUID) -> bool:
        """
        Delete a submission record from the database.

        Args:
            submission_id: UUID of the submission to delete.

        Returns:
            True if deleted, False if submission was not found.
        """
        submission = self.get_submission(submission_id)
        if not submission:
            return False

        try:
            self.session.delete(submission)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

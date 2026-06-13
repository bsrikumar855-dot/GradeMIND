"""
GradeMIND Submission Service.
Business logic layer that orchestrates the submission lifecycle:
upload → OCR → evaluation → report generation.
Integrates with the existing AI pipeline components.
"""

import os
import sys
import json
import logging
import traceback
from uuid import UUID
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.models.submission import Submission, SubmissionStatus
from app.models.exam import Exam
from app.repositories.submission_repository import SubmissionRepository
from app.services import storage_service

logger = logging.getLogger("GradeMIND.SubmissionService")


class SubmissionService:
    """
    Service class encapsulating all submission business logic.
    Coordinates between the repository layer, storage service, and AI pipeline.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = SubmissionRepository(db)

    # ────────────────────────────────────────────
    # Upload & CRUD
    # ────────────────────────────────────────────

    async def upload_submission(
        self,
        exam_id: UUID,
        student_name: str,
        student_roll_number: str,
        file_content: bytes,
        original_filename: str
    ) -> Submission:
        """
        Create a new submission record and persist the uploaded answer sheet.

        Args:
            exam_id: UUID of the exam this submission belongs to.
            student_name: Full name of the student.
            student_roll_number: Student roll/ID number.
            file_content: Raw bytes of the uploaded file.
            original_filename: Original filename for extension detection.

        Returns:
            Created Submission model instance with UPLOADED status.

        Raises:
            ValueError: If the referenced exam does not exist.
        """
        # Verify the exam exists
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise ValueError(f"Exam with ID {exam_id} does not exist.")

        # Generate storage path and save file
        file_path = storage_service.generate_file_path(
            category="answer_sheets",
            exam_id=str(exam_id),
            identifier=student_roll_number,
            original_filename=original_filename
        )
        await storage_service.save_file(file_content, file_path)

        # Create database record
        submission = Submission(
            exam_id=exam_id,
            student_name=student_name,
            student_roll_number=student_roll_number,
            answer_sheet_path=file_path,
            status=SubmissionStatus.UPLOADED,
            total_marks=float(exam.total_marks)
        )

        return self.repo.create_submission(submission)

    def get_submission(self, submission_id: UUID) -> Optional[Submission]:
        """Retrieve a single submission by ID."""
        return self.repo.get_submission(submission_id)

    def list_submissions(
        self,
        exam_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Submission], int]:
        """
        List submissions with optional filters and return total count.

        Returns:
            Tuple of (list of submissions, total count).
        """
        submissions = self.repo.list_submissions(
            exam_id=exam_id, status=status, skip=skip, limit=limit
        )
        total = self.repo.count_submissions(exam_id=exam_id, status=status)
        return submissions, total

    def get_submission_status(self, submission_id: UUID) -> Optional[Submission]:
        """Get submission status — lightweight alias for get_submission."""
        return self.repo.get_submission(submission_id)

    def delete_submission(self, submission_id: UUID) -> bool:
        """Delete a submission and its associated files."""
        submission = self.repo.get_submission(submission_id)
        if not submission:
            return False

        # Clean up stored files
        for path_attr in [
            "answer_sheet_path", "ocr_output_path",
            "evaluation_output_path", "report_path"
        ]:
            file_path = getattr(submission, path_attr, None)
            if file_path and os.path.exists(file_path):
                storage_service.delete_file(file_path)

        return self.repo.delete_submission(submission_id)

    # ────────────────────────────────────────────
    # Background Processing Pipeline
    # ────────────────────────────────────────────

    def process_submission(self, submission_id: UUID) -> None:
        """
        Full background processing pipeline for a submission.
        Runs OCR → Evaluation → Report Generation sequentially.
        Updates status at each stage.

        This method is designed to be invoked via FastAPI BackgroundTasks.
        """
        logger.info(f"Starting background processing for submission {submission_id}")

        try:
            # Stage 1: OCR
            self._update_status(submission_id, SubmissionStatus.PROCESSING, ocr_status="PROCESSING")
            self.trigger_ocr(submission_id)

            # Stage 2: Evaluation
            self._update_status(submission_id, SubmissionStatus.EVALUATING, evaluation_status="PROCESSING")
            self.trigger_evaluation(submission_id)

            # Stage 3: Report Generation
            self.generate_report(submission_id)

            # Mark as complete
            self._update_status(submission_id, SubmissionStatus.COMPLETED)
            logger.info(f"Submission {submission_id} processing completed successfully.")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Processing failed for submission {submission_id}: {error_msg}")
            self.repo.update_status(
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                error_message=str(e)
            )

    # ────────────────────────────────────────────
    # OCR Integration
    # ────────────────────────────────────────────

    def trigger_ocr(self, submission_id: UUID) -> None:
        """
        Execute OCR processing on the submission's answer sheet.
        Uses the existing AI/ocr/ocr_manager.py OCRManager.
        """
        submission = self.repo.get_submission(submission_id)
        if not submission or not submission.answer_sheet_path:
            raise ValueError(f"Submission {submission_id} has no answer sheet to process.")

        try:
            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            from AI.ocr.ocr_manager import OCRManager

            ocr_manager = OCRManager()
            ocr_result = ocr_manager.extract_text(
                image_path=submission.answer_sheet_path,
                submission_id=1
            )

            # Save OCR output as JSON
            ocr_output_path = storage_service.generate_file_path(
                category="ocr_outputs",
                exam_id=str(submission.exam_id),
                identifier=submission.student_roll_number,
                original_filename="ocr_output.json"
            )

            ocr_json = ocr_result.model_dump_json(indent=2)
            storage_service.save_text_file(ocr_json, ocr_output_path)

            # Update submission with OCR results
            self.repo.update_results(
                submission_id=submission_id,
                ocr_output_path=ocr_output_path,
                ocr_confidence=ocr_result.confidence
            )
            self._update_status(
                submission_id, SubmissionStatus.OCR_COMPLETE, ocr_status="COMPLETED"
            )

            logger.info(
                f"OCR completed for submission {submission_id}. "
                f"Confidence: {ocr_result.confidence:.4f}, Lines: {len(ocr_result.lines)}"
            )

        except Exception as e:
            logger.error(f"OCR processing failed for submission {submission_id}: {e}")
            self._update_status(
                submission_id, SubmissionStatus.FAILED,
                ocr_status="FAILED", error_message=str(e)
            )
            raise

    # ────────────────────────────────────────────
    # Evaluation Integration
    # ────────────────────────────────────────────

    def trigger_evaluation(self, submission_id: UUID) -> None:
        """
        Execute AI evaluation on OCR output.
        Integrates with backend/app/services/ai_service.py evaluate_submission.
        """
        submission = self.repo.get_submission(submission_id)
        if not submission or not submission.ocr_output_path:
            raise ValueError(f"Submission {submission_id} has no OCR output to evaluate.")

        try:
            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            # Load OCR output
            with open(submission.ocr_output_path, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)

            # Run the AI evaluation engine on the OCR data
            from app.services.ai_service import evaluate_submission
            
            evaluation_result = evaluate_submission(
                submission_id=str(submission.id),
                exam_id=str(submission.exam_id),
                ocr_output=ocr_data
            )

            # Save evaluation output as JSON
            eval_output_path = storage_service.generate_file_path(
                category="evaluation_outputs",
                exam_id=str(submission.exam_id),
                identifier=submission.student_roll_number,
                original_filename="evaluation_output.json"
            )
            storage_service.save_text_file(
                json.dumps(evaluation_result, indent=2, default=str),
                eval_output_path
            )

            # Update submission with evaluation results
            self.repo.update_results(
                submission_id=submission_id,
                evaluation_output_path=eval_output_path,
                obtained_marks=evaluation_result.get("total_score", 0.0),
                evaluation_confidence=evaluation_result.get("confidence_score", 0.0)
            )
            self._update_status(
                submission_id, SubmissionStatus.EVALUATING,
                evaluation_status="COMPLETED"
            )

            logger.info(f"Evaluation completed for submission {submission_id}")

        except Exception as e:
            logger.error(f"Evaluation failed for submission {submission_id}: {e}")
            self._update_status(
                submission_id, SubmissionStatus.FAILED,
                evaluation_status="FAILED", error_message=str(e)
            )
            raise

    # ────────────────────────────────────────────
    # Report Generation
    # ────────────────────────────────────────────

    def generate_report(self, submission_id: UUID) -> None:
        """
        Generate a report from the evaluation outputs using the existing
        AI/reports/report_data_builder.py ReportDataBuilder.
        """
        submission = self.repo.get_submission(submission_id)
        if not submission or not submission.evaluation_output_path:
            raise ValueError(f"Submission {submission_id} has no evaluation output for report generation.")

        try:
            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            # Load evaluation data
            with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)

            # Import AI Schemas and Report Builder
            from AI.schemas.evaluation_schema import SubmissionEvaluation as AISubmissionEvaluation, ReportPayload
            from AI.reports.report_data_builder import ReportDataBuilder

            # Reconstruct the Pydantic model from stored evaluation dict
            ai_eval = AISubmissionEvaluation.model_validate(eval_data)
            builder = ReportDataBuilder()

            # Compile analytics, dashboards, and PDF payloads
            analytics_payload = builder.build_analytics([ai_eval])
            teacher_dash = builder.build_teacher_dashboard([ai_eval])
            student_dash = builder.build_student_dashboard(ai_eval)

            # Generate target JSON report path
            report_path = storage_service.generate_file_path(
                category="reports",
                exam_id=str(submission.exam_id),
                identifier=submission.student_roll_number,
                original_filename="report.json"
            )

            # Generate target PDF report path
            pdf_path = os.path.splitext(report_path)[0] + ".pdf"
            builder.generate_pdf_report(ai_eval, pdf_path)

            # Pack all payloads into Final Pydantic ReportPayload schema
            final_payload = ReportPayload(
                pdf_url=pdf_path,
                evaluation_summary=ai_eval,
                analytics=analytics_payload,
                teacher_dashboard=teacher_dash,
                student_dashboard=student_dash,
                metadata={
                    "student_name": submission.student_name,
                    "student_roll_number": submission.student_roll_number,
                    "exam_id": str(submission.exam_id)
                }
            )

            # Save report JSON file
            storage_service.save_text_file(
                final_payload.model_dump_json(indent=2),
                report_path
            )

            # Update submission with report path
            self.repo.update_results(
                submission_id=submission_id,
                report_path=report_path
            )

            logger.info(f"Report generated for submission {submission_id}: {report_path} and {pdf_path}")

        except Exception as e:
            logger.error(f"Report generation failed for submission {submission_id}: {e}")
            raise

    # ────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────

    def _update_status(
        self,
        submission_id: UUID,
        status: str,
        ocr_status: Optional[str] = None,
        evaluation_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Internal helper to update submission status fields."""
        self.repo.update_status(
            submission_id=submission_id,
            status=status,
            ocr_status=ocr_status,
            evaluation_status=evaluation_status,
            error_message=error_message
        )

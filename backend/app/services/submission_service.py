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
import re
from uuid import UUID
from typing import Optional, List, Tuple, Dict, Any

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
        logger.info(
            "UPLOAD_STAGE storage_path_generated exam_id=%s student_roll_number=%s path=%s",
            exam_id,
            student_roll_number,
            file_path,
        )
        await storage_service.save_file(file_content, file_path)
        logger.info("UPLOAD_STAGE file_saved path=%s bytes=%s", file_path, len(file_content))

        # Create database record
        submission = Submission(
            exam_id=exam_id,
            student_name=student_name,
            student_roll_number=student_roll_number,
            answer_sheet_path=file_path,
            status=SubmissionStatus.UPLOADED,
            total_marks=float(exam.total_marks)
        )

        created = self.repo.create_submission(submission)
        logger.info(
            "UPLOAD_STAGE db_record_created submission_id=%s status=%s total_marks=%s",
            created.id,
            created.status,
            created.total_marks,
        )
        return created

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

    def list_evaluated_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return evaluated submissions formatted for report-picker empty states."""
        submissions = (
            self.db.query(Submission)
            .filter(Submission.status == SubmissionStatus.COMPLETED)
            .order_by(Submission.updated_at.desc())
            .limit(limit)
            .all()
        )
        reports = []
        for submission in submissions:
            exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()
            reports.append({
                "submissionId": str(submission.id),
                "examId": str(submission.exam_id),
                "examTitle": exam.title if exam else "Unknown Exam",
                "examName": exam.title if exam else "Unknown Exam",
                "studentName": submission.student_name,
                "studentRollNumber": submission.student_roll_number,
                "obtainedMarks": submission.obtained_marks,
                "totalMarks": submission.total_marks,
                "score": self._format_score(submission.obtained_marks, submission.total_marks),
                "date": submission.updated_at,
                "status": submission.status,
                "createdAt": submission.created_at,
                "updatedAt": submission.updated_at,
                "resultsUrl": f"/results?submissionId={submission.id}",
                "feedbackUrl": f"/feedback?submissionId={submission.id}",
                "viewResultUrl": f"/results?submissionId={submission.id}",
                "viewFeedbackUrl": f"/feedback?submissionId={submission.id}",
            })
        return reports

    def _format_score(self, obtained: Optional[float], total: Optional[float]) -> str:
        if obtained is None and total is None:
            return "Not scored"
        if total is None:
            return f"{obtained:g}"
        if obtained is None:
            return f"0/{total:g}"
        return f"{obtained:g}/{total:g}"

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
            logger.info("PIPELINE_STAGE ocr_start submission_id=%s", submission_id)
            self._update_status(
                submission_id,
                SubmissionStatus.PROCESSING,
                ocr_status="PROCESSING",
                error_message=""
            )
            self.trigger_ocr(submission_id)
            logger.info("PIPELINE_STAGE ocr_completed submission_id=%s", submission_id)

            # Stage 2: Evaluation
            logger.info("PIPELINE_STAGE evaluation_start submission_id=%s", submission_id)
            self._update_status(submission_id, SubmissionStatus.EVALUATING, evaluation_status="PROCESSING")
            self.trigger_evaluation(submission_id)
            logger.info("PIPELINE_STAGE evaluation_completed submission_id=%s", submission_id)

            # Stage 3: Report Generation
            logger.info("PIPELINE_STAGE report_start submission_id=%s", submission_id)
            self.generate_report(submission_id)
            logger.info("PIPELINE_STAGE report_completed submission_id=%s", submission_id)

            # Mark as complete
            self._update_status(submission_id, SubmissionStatus.COMPLETED, error_message="")
            logger.info(f"Submission {submission_id} processing completed successfully.")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error("PIPELINE_STAGE failed submission_id=%s error=%s", submission_id, error_msg)
            self.repo.update_status(
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                error_message="Evaluation could not be completed. Please retry the submission."
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
            logger.info(
                "OCR_STAGE start submission_id=%s answer_sheet_path=%s",
                submission_id,
                submission.answer_sheet_path,
            )

            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            from AI.ocr.ocr_manager import OCRManager

            ocr_manager = OCRManager()
            ocr_result = ocr_manager.extract_text(
                image_path=submission.answer_sheet_path,
                submission_id=str(submission.id)
            )
            logger.info(
                "OCR_STAGE extraction_completed submission_id=%s confidence=%s lines=%s",
                submission_id,
                ocr_result.confidence,
                len(ocr_result.lines),
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
            logger.info("OCR_STAGE output_saved submission_id=%s path=%s", submission_id, ocr_output_path)

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
            logger.exception("OCR_STAGE failed submission_id=%s error=%s", submission_id, e)
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
            logger.info(
                "EVALUATION_STAGE start submission_id=%s ocr_output_path=%s",
                submission_id,
                submission.ocr_output_path,
            )

            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            # Load OCR output
            with open(submission.ocr_output_path, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
            logger.info(
                "EVALUATION_STAGE ocr_loaded submission_id=%s lines=%s confidence=%s",
                submission_id,
                len(ocr_data.get("lines", [])),
                ocr_data.get("confidence"),
            )

            # Run the AI evaluation engine on the OCR data
            from app.services.ai_service import evaluate_submission
            answer_key_metadata = self._load_answer_key_metadata(submission)
            exam_context = self._load_exam_context(submission)
            logger.info(
                "EVALUATION_STAGE context_loaded submission_id=%s mode=%s answer_key=%s questions=%s",
                submission_id,
                exam_context.get("evaluation_mode"),
                bool(answer_key_metadata),
                len(exam_context.get("questions") or {}),
            )
            
            evaluation_result = evaluate_submission(
                submission_id=str(submission.id),
                exam_id=str(submission.exam_id),
                ocr_output=ocr_data,
                exams_metadata=answer_key_metadata,
                exam_context=exam_context
            )
            logger.info(
                "EVALUATION_STAGE service_completed submission_id=%s total_score=%s max_possible=%s confidence=%s",
                submission_id,
                evaluation_result.get("total_score"),
                evaluation_result.get("max_possible"),
                evaluation_result.get("confidence_score"),
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
            logger.info("EVALUATION_STAGE output_saved submission_id=%s path=%s", submission_id, eval_output_path)

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

            logger.info(
                "EVALUATION_STAGE db_results_updated submission_id=%s obtained_marks=%s confidence=%s",
                submission_id,
                evaluation_result.get("total_score", 0.0),
                evaluation_result.get("confidence_score", 0.0),
            )

        except Exception as e:
            logger.exception("EVALUATION_STAGE failed submission_id=%s error=%s", submission_id, e)
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
            logger.info(
                "REPORT_STAGE start submission_id=%s evaluation_output_path=%s",
                submission_id,
                submission.evaluation_output_path,
            )

            # Add AI directory to path for imports
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)

            # Load evaluation data
            with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
            logger.info(
                "REPORT_STAGE evaluation_loaded submission_id=%s total_score=%s",
                submission_id,
                eval_data.get("total_score"),
            )

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

            exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()

            # Generate target PDF report path
            pdf_path = os.path.splitext(report_path)[0] + ".pdf"
            builder.generate_pdf_report(
                ai_eval,
                pdf_path,
                metadata={
                    "student_name": submission.student_name,
                    "student_roll_number": submission.student_roll_number,
                    "exam_id": str(submission.exam_id),
                    "exam_title": exam.title if exam else "Assessment",
                    "evaluation_mode": eval_data.get("evaluation_mode", "ANSWER_KEY"),
                },
            )

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
                    "exam_id": str(submission.exam_id),
                    "evaluation_mode": eval_data.get("evaluation_mode", "ANSWER_KEY")
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
            logger.exception("REPORT_STAGE failed submission_id=%s error=%s", submission_id, e)
            raise

    def ensure_report_artifacts(self, submission_id: UUID) -> Tuple[str, str]:
        """
        Ensure JSON and PDF report files exist, regenerating from evaluation output when possible.
        """
        submission = self.repo.get_submission(submission_id)
        if not submission:
            raise ValueError("SUBMISSION_NOT_FOUND")
        if not submission.evaluation_output_path or not os.path.exists(submission.evaluation_output_path):
            raise ValueError("EVALUATION_OUTPUT_MISSING")

        report_path = submission.report_path
        pdf_path = self._pdf_path_for_report(report_path) if report_path else None
        needs_generation = (
            not report_path
            or not os.path.exists(report_path)
            or not pdf_path
            or not os.path.exists(pdf_path)
            or self._is_broken_pdf(pdf_path)
        )
        if needs_generation:
            logger.warning(
                "Report artifacts missing or stale; regenerating before download. submission_id=%s report_path=%s pdf_path=%s",
                submission_id,
                report_path,
                pdf_path,
            )
            self.generate_report(submission_id)
            submission = self.repo.get_submission(submission_id)
            report_path = submission.report_path
            pdf_path = self._pdf_path_for_report(report_path)

        if not report_path or not os.path.exists(report_path):
            raise ValueError("REPORT_FILE_MISSING")
        if not pdf_path or not os.path.exists(pdf_path):
            raise ValueError("PDF_FILE_MISSING")
        return report_path, pdf_path

    def generate_study_plan_pdf(self, submission_id: UUID) -> str:
        """Generate a focused study-plan PDF from existing evaluation feedback."""
        report_path, _ = self.ensure_report_artifacts(submission_id)
        submission = self.repo.get_submission(submission_id)

        with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        recommendations = eval_data.get("study_recommendations") or []
        improvements = eval_data.get("improvements") or []
        weaknesses = eval_data.get("weaknesses") or []
        topics = recommendations or [
            "Core Concepts From This Exam",
            "Answer Structure And Explanation",
            "Question-Specific Terminology",
        ]
        plan_path = os.path.splitext(report_path)[0] + "_study_plan.pdf"

        from AI.reports.report_data_builder import ReportDataBuilder

        builder = ReportDataBuilder()
        lines = [
            "GradeMIND Study Plan",
            f"Student: {submission.student_name}",
            f"Roll Number: {submission.student_roll_number}",
            f"Submission ID: {submission.id}",
            "",
            "Study Topics:",
            *[f"- {topic}" for topic in topics[:6]],
            "",
            "Practice Focus:",
            *[f"- {item}" for item in (improvements or weaknesses)[:6]],
        ]
        builder.generate_text_pdf(lines, plan_path)
        return plan_path

    def _pdf_path_for_report(self, report_path: Optional[str]) -> Optional[str]:
        if not report_path:
            return None
        if report_path.lower().endswith(".pdf"):
            return report_path
        return os.path.splitext(report_path)[0] + ".pdf"

    def _is_broken_pdf(self, pdf_path: Optional[str]) -> bool:
        if not pdf_path or not os.path.exists(pdf_path):
            return True
        try:
            size = os.path.getsize(pdf_path)
            if size < 50_000:
                logger.warning("PDF is too small and will be regenerated: path=%s size=%s", pdf_path, size)
                return True
            with open(pdf_path, "rb") as f:
                sample = f.read(2_000_000)
            stale_markers = [
                b"Install pdflatex",
                b"LaTeX source file was generated",
                b"ReportLab",
            ]
            if any(marker in sample for marker in stale_markers):
                logger.warning("PDF contains stale fallback marker and will be regenerated: path=%s", pdf_path)
                return True
        except OSError as exc:
            logger.warning("Could not inspect PDF; will regenerate. path=%s error=%s", pdf_path, exc)
            return True
        return False

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
        logger.info(
            "DB_STAGE status_update_requested submission_id=%s status=%s ocr_status=%s evaluation_status=%s error=%s",
            submission_id,
            status,
            ocr_status,
            evaluation_status,
            error_message,
        )
        self.repo.update_status(
            submission_id=submission_id,
            status=status,
            ocr_status=ocr_status,
            evaluation_status=evaluation_status,
            error_message=error_message
        )

    def _load_answer_key_metadata(self, submission: Submission) -> Optional[dict]:
        """
        Build answer-key evaluation metadata when an answer key is configured.
        Returns None when the exam is intentionally configured for autonomous evaluation.
        """
        exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if not exam:
            raise ValueError(f"Exam {submission.exam_id} does not exist.")

        if not exam.answer_key_url:
            return None

        if not os.path.exists(exam.answer_key_url):
            raise ValueError(
                f"Exam {submission.exam_id} has an answer key path that is not readable."
            )

        answer_key_text = self._load_source_file_text(exam.answer_key_url, str(exam.id), "answer key")

        if not answer_key_text:
            raise ValueError(f"Exam {submission.exam_id} answer key is empty; evaluation cannot run.")

        question_text = self._load_question_paper_text(exam)

        return {
            "question_1": {
                "text": question_text,
                "answer_key": answer_key_text,
            }
        }

    def _load_exam_context(self, submission: Submission) -> dict:
        """Build question context used by autonomous evaluation."""
        exam = self.db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if not exam:
            raise ValueError(f"Exam {submission.exam_id} does not exist.")

        question_text = self._load_question_paper_text(exam)

        questions = self._parse_question_context(question_text, float(exam.total_marks))
        return {
            "exam_id": str(exam.id),
            "subject": exam.subject,
            "total_marks": float(exam.total_marks),
            "evaluation_mode": "ANSWER_KEY" if exam.answer_key_url else "AI_AUTONOMOUS",
            "questions": questions,
        }

    def _load_question_paper_text(self, exam: Exam) -> str:
        if not exam.question_paper_url:
            raise ValueError(
                f"Exam {exam.id} has no uploaded question paper; refusing to use exam title or subject as question text."
            )
        if not os.path.exists(exam.question_paper_url):
            raise ValueError(f"Exam {exam.id} question paper path is not readable.")

        question_text = self._load_source_file_text(exam.question_paper_url, str(exam.id), "question paper")

        if not question_text:
            raise ValueError(
                f"Exam {exam.id} question paper contains no extractable text; refusing to use exam metadata."
            )
        return question_text

    def _load_source_file_text(self, file_path: str, source_id: str, label: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if ai_root not in sys.path:
                sys.path.insert(0, ai_root)
            from AI.ocr.ocr_manager import OCRManager

            doc = OCRManager().extract_pdf_text(file_path, source_id)
            return "\n".join(line.text for line in doc.lines).strip()

        if ext in {".txt", ".json"}:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()

        ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if ai_root not in sys.path:
            sys.path.insert(0, ai_root)
        from AI.ocr.ocr_manager import OCRManager

        doc = OCRManager().extract_text(file_path, source_id)
        text = "\n".join(line.text for line in doc.lines).strip()
        if not text:
            raise ValueError(f"Exam source {label} has no extractable text.")
        return text

    def _parse_question_context(self, question_text: str, total_marks: float) -> dict:
        """Parse plain-text question papers into a question map."""
        text = re.sub(r"\s+", " ", question_text or "").strip()
        if not text:
            raise ValueError("Question text is required for evaluation.")

        matches = list(re.finditer(r"\b(?:Q|Question)\s*\.?\s*(\d+)\b|(?:^|\s)(\d+)[\.\)]\s+", text, re.IGNORECASE))
        if not matches:
            marks = self._extract_marks(text) or total_marks
            return {"question_1": {"text": text, "marks": marks}}

        questions = {}
        for idx, match in enumerate(matches):
            q_num = match.group(1) or match.group(2) or str(idx + 1)
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            q_text = text[start:end].strip()
            if q_text:
                questions[f"question_{q_num}"] = {
                    "text": q_text,
                    "marks": self._extract_marks(q_text),
                }

        unresolved = [key for key, value in questions.items() if value["marks"] is None]
        if unresolved:
            per_question = round(total_marks / len(questions), 2)
            for key in unresolved:
                questions[key]["marks"] = per_question

        return questions

    def _extract_marks(self, text: str) -> Optional[float]:
        match = re.search(r"[\[\(]\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*[\]\)]", text, re.IGNORECASE)
        return float(match.group(1)) if match else None

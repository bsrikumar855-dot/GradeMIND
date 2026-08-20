import logging
import traceback
from uuid import UUID
from datetime import datetime, timezone
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.core.database import SessionLocal
from app.models.submission import Submission, SubmissionStatus
from app.services.submission_service import SubmissionService

logger = logging.getLogger("GradeMIND.WorkerTasks")

def _get_submission_service(db):
    return SubmissionService(db)

import os

def _get_db_session():
    if "pytest" in sys.modules:
        try:
            from tests.conftest import TestingSessionLocal
            return TestingSessionLocal()
        except ImportError:
            pass
    return SessionLocal()

def _update_submission_state(submission_id: UUID, status: str, **kwargs):
    db = _get_db_session()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = status
            for k, v in kwargs.items():
                setattr(submission, k, v)
            db.commit()
    finally:
        db.close()

def _mark_failed(submission_id: UUID, stage: str, exc: Exception, retry_count: int):
    error_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
    _update_submission_state(
        submission_id,
        SubmissionStatus.FAILED,
        failed_stage=stage,
        error_type=type(exc).__name__,
        error_message=error_msg,
        retry_count=retry_count
    )

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_process_ocr(self, submission_id: str):
    logger.info(f"Starting OCR task for submission {submission_id}")
    submission_uuid = UUID(submission_id)
    _update_submission_state(
        submission_uuid,
        SubmissionStatus.PROCESSING_OCR,
        ocr_started_at=datetime.now(timezone.utc)
    )
    
    db = _get_db_session()
    try:
        service = _get_submission_service(db)
        try:
            # Idempotency check: if OCR output path already exists, we skip running it again
            submission = db.query(Submission).filter(Submission.id == submission_uuid).first()
            if submission and not submission.ocr_output_path:
                service.trigger_ocr(submission_uuid)
                
            _update_submission_state(
                submission_uuid,
                SubmissionStatus.OCR_COMPLETE,
                ocr_completed_at=datetime.now(timezone.utc)
            )
            # Queue next stage
            try:
                task_evaluate_answers.delay(submission_id)
            except Exception:
                task_evaluate_answers(submission_id)
            
        except Exception as exc:
            logger.error(f"OCR failed for {submission_id}: {exc}")
            try:
                self.retry(exc=exc)
            except MaxRetriesExceededError:
                _mark_failed(submission_uuid, "OCR", exc, self.request.retries)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_evaluate_answers(self, submission_id: str):
    logger.info(f"Starting Evaluation task for submission {submission_id}")
    submission_uuid = UUID(submission_id)
    _update_submission_state(
        submission_uuid,
        SubmissionStatus.EVALUATING,
        evaluation_started_at=datetime.now(timezone.utc)
    )
    
    db = _get_db_session()
    try:
        service = _get_submission_service(db)
        try:
            # Idempotency check
            submission = db.query(Submission).filter(Submission.id == submission_uuid).first()
            if submission and not submission.evaluation_output_path:
                service.trigger_evaluation(submission_uuid)
                
            _update_submission_state(
                submission_uuid,
                SubmissionStatus.VERIFYING, # Maps to evaluation complete / report gen start
                evaluation_completed_at=datetime.now(timezone.utc)
            )
            # Queue next stage
            try:
                task_generate_report.delay(submission_id)
            except Exception:
                task_generate_report(submission_id)
            
        except Exception as exc:
            logger.error(f"Evaluation failed for {submission_id}: {exc}")
            try:
                self.retry(exc=exc)
            except MaxRetriesExceededError:
                _mark_failed(submission_uuid, "EVALUATION", exc, self.request.retries)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_generate_report(self, submission_id: str):
    logger.info(f"Starting Report Generation task for submission {submission_id}")
    submission_uuid = UUID(submission_id)
    
    db = _get_db_session()
    try:
        service = _get_submission_service(db)
        try:
            # Ensure evaluation exists before generating report
            submission = db.query(Submission).filter(Submission.id == submission_uuid).first()
            if submission and not submission.report_path:
                service.generate_report(submission_uuid)
                
            _update_submission_state(
                submission_uuid,
                SubmissionStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc)
            )
            
        except Exception as exc:
            logger.error(f"Report Generation failed for {submission_id}: {exc}")
            try:
                self.retry(exc=exc)
            except MaxRetriesExceededError:
                _mark_failed(submission_uuid, "REPORT", exc, self.request.retries)
    finally:
        db.close()

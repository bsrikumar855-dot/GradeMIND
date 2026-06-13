"""
GradeMIND End-to-End Pipeline Integration Test Suite.
Verifies the complete integration of OCR, evaluation, and report generation (JSON/PDF).
"""

import io
import os
import json
import pytest
from uuid import uuid4, UUID
from fastapi.testclient import TestClient

from app.core.database import Base
from app.main import app
from app.db.session import get_db
from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus
from app.services.submission_service import SubmissionService
from app.services import storage_service
from tests.conftest import engine, TestingSessionLocal


# ────────────────────────────────────────────
# Auth Mock Helper
# ────────────────────────────────────────────

def mock_teacher_auth():
    """Mock authentication as a TEACHER user."""
    user_id = uuid4()
    def override_get_current_user():
        return {"id": user_id, "role": "TEACHER", "email": "teacher@test.com"}

    def override_require_teacher_or_admin():
        return override_get_current_user()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_teacher_or_admin] = override_require_teacher_or_admin
    return user_id


# ────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create and tear down all tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide a direct database session for test setup operations."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_exam(db_session):
    """Create a sample exam in the database."""
    teacher_id = uuid4()
    exam = Exam(
        teacher_id=teacher_id,
        title="Integration Science Exam",
        subject="Science",
        total_marks=15,  # 3 questions worth 5 marks each in our default fallback metadata
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def sample_answer_sheet():
    """Return mock answer sheet content (valid enough for image/png validation)."""
    # Minimal 1x1 white pixel PNG
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return png_content


client = TestClient(app)


# ────────────────────────────────────────────
# Pipeline Integration Tests
# ────────────────────────────────────────────

class TestPipelineIntegration:
    """End-to-end test validating OCR to Evaluation and Report Generation integration."""

    def test_end_to_end_pipeline_success(self, sample_exam, sample_answer_sheet, db_session):
        """
        Verify that a complete upload, OCR, evaluation, and report generation cycle
        progresses successfully and produces correct JSON and PDF files in local storage.
        """
        # 1. Setup Auth
        from app.api.auth_deps import get_current_user, require_teacher_or_admin
        teacher_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: {"id": teacher_id, "role": "TEACHER", "email": "teacher@test.com"}
        app.dependency_overrides[require_teacher_or_admin] = lambda: {"id": teacher_id, "role": "TEACHER", "email": "teacher@test.com"}

        # 2. Upload the file via TestClient
        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Integration Student",
                "student_roll_number": "ROLL_E2E_011",
            },
            files={"file": ("answers.png", io.BytesIO(sample_answer_sheet), "image/png")},
        )

        assert response.status_code == 201
        res_data = response.json()
        submission_id = UUID(res_data["id"])

        # 3. Synchronously run the processing pipeline using SubmissionService
        service = SubmissionService(db_session)
        service.process_submission(submission_id)

        # 4. Reload submission from database to assert states
        db_session.expire_all()
        submission = db_session.query(Submission).filter(Submission.id == submission_id).first()

        assert submission is not None
        assert submission.status == SubmissionStatus.COMPLETED
        assert submission.ocr_status == "COMPLETED"
        assert submission.evaluation_status == "COMPLETED"
        
        # Verify OCR output exists on disk
        assert submission.ocr_output_path is not None
        assert os.path.exists(submission.ocr_output_path)
        with open(submission.ocr_output_path, "r", encoding="utf-8") as f:
            ocr_content = json.load(f)
            assert ocr_content["confidence"] > 0
            assert len(ocr_content["lines"]) > 0

        # Verify Evaluation output exists on disk
        assert submission.evaluation_output_path is not None
        assert os.path.exists(submission.evaluation_output_path)
        with open(submission.evaluation_output_path, "r", encoding="utf-8") as f:
            eval_content = json.load(f)
            assert eval_content["submission_id"] == 101
            assert eval_content["total_score"] > 0
            assert eval_content["max_possible"] == 15.0  # 3 default questions * 5 marks

        # Verify Report output exists on disk (JSON format)
        assert submission.report_path is not None
        assert os.path.exists(submission.report_path)
        with open(submission.report_path, "r", encoding="utf-8") as f:
            report_content = json.load(f)
            assert report_content["evaluation_summary"]["submission_id"] == 101
            assert "analytics" in report_content
            assert "teacher_dashboard" in report_content
            assert "student_dashboard" in report_content

        # Verify PDF report output exists on disk
        pdf_path = os.path.splitext(submission.report_path)[0] + ".pdf"
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read(10)
            assert pdf_bytes.startswith(b"%PDF-1.4")

        # Clean up files created
        for p in [submission.answer_sheet_path, submission.ocr_output_path, submission.evaluation_output_path, submission.report_path, pdf_path]:
            if p and os.path.exists(p):
                os.remove(p)

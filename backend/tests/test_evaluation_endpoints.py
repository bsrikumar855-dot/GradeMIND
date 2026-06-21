"""
GradeMIND Evaluation Service APIs Test Suite.
Tests POST /evaluate, GET /evaluation/{id}, GET /reports/{id}, and GET /analytics/class/{id}.
"""

import json
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.core.database import Base
from app.main import app
from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus
from tests.conftest import engine, TestingSessionLocal

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create and tear down database schema for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Direct database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_teacher_id():
    """Constant UUID for test teacher."""
    return uuid4()


@pytest.fixture(autouse=True)
def mock_auth(test_teacher_id):
    """Mock authentication for evaluation tests."""
    from app.api.auth_deps import get_current_user, require_teacher_or_admin
    app.dependency_overrides[get_current_user] = lambda: {"id": test_teacher_id, "role": "TEACHER", "email": "teacher@test.com"}
    app.dependency_overrides[require_teacher_or_admin] = lambda: {"id": test_teacher_id, "role": "TEACHER", "email": "teacher@test.com"}
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_background_processing(monkeypatch):
    """Mock the background task process to prevent it from executing during tests."""
    import app.api.evaluation
    # Replace the background task runner with a no-op
    monkeypatch.setattr(app.api.evaluation, "_run_background_processing", lambda *args, **kwargs: None)


@pytest.fixture
def sample_data(db_session, test_teacher_id):
    """Create sample exams and submissions."""
    exam = Exam(
        id=uuid4(),
        teacher_id=test_teacher_id,
        title="Chemistry Midterm",
        subject="Chemistry",
        total_marks=100
    )
    db_session.add(exam)
    db_session.commit()

    sub_completed = Submission(
        id=uuid4(),
        exam_id=exam.id,
        student_name="Diana Prince",
        student_roll_number="CHEM-001",
        answer_sheet_path="mock_chem1.png",
        ocr_status="COMPLETED",
        evaluation_status="COMPLETED",
        status=SubmissionStatus.COMPLETED,
        obtained_marks=92.5,
        total_marks=100.0,
        evaluation_confidence=0.96,
        evaluation_output_path=None,  # Will write mock file during specific test
        report_path=None  # Will write mock file during specific test
    )
    db_session.add(sub_completed)

    sub_pending = Submission(
        id=uuid4(),
        exam_id=exam.id,
        student_name="Bruce Wayne",
        student_roll_number="CHEM-002",
        answer_sheet_path="mock_chem2.png",
        ocr_status="PROCESSING",
        evaluation_status="PENDING",
        status=SubmissionStatus.PROCESSING
    )
    db_session.add(sub_pending)
    db_session.commit()

    return {
        "exam": exam,
        "sub_completed": sub_completed,
        "sub_pending": sub_pending
    }


class TestEvaluationAPIs:
    """Validates the new evaluation endpoints."""

    def test_post_evaluate_success(self, sample_data, mock_background_processing):
        """Verify POST /evaluate accepts a submission and triggers background tasks."""
        sub_id = sample_data["sub_pending"].id
        response = client.post("/evaluate", json={"submission_id": str(sub_id)})
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["submission_id"] == str(sub_id)
        assert "started" in data["message"].lower()

    def test_post_evaluate_not_found(self, mock_background_processing):
        """Verify POST /evaluate returns 404 for nonexistent submissions."""
        nonexistent_id = uuid4()
        response = client.post("/evaluate", json={"submission_id": str(nonexistent_id)})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_evaluation_without_details(self, sample_data):
        """Verify GET /evaluation/{id} returns basic DB details when JSON file is missing."""
        sub = sample_data["sub_completed"]
        response = client.get(f"/evaluation/{sub.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["submission_id"] == str(sub.id)
        assert data["student_name"] == "Diana Prince"
        assert data["obtained_marks"] == 92.5
        assert data["evaluation_output"] is None

    def test_get_evaluation_with_details(self, sample_data, tmp_path, db_session):
        """Verify GET /evaluation/{id} successfully reads and appends stored JSON details."""
        sub = sample_data["sub_completed"]

        eval_details = {
            "evaluation_mode": "AI_AUTONOMOUS",
            "strengths": ["Clear work", "Correct chemistry terminology"],
            "weaknesses": ["None"],
            "summary": "Excellent performance.",
            "questions": [
                {
                    "question_number": "1",
                    "max_marks": 10.0,
                    "score_awarded": 10.0,
                    "student_answer_extracted": "H2O is water",
                    "confidence": 0.98
                }
            ]
        }

        temp_file = str(tmp_path / "mock_eval_detail.json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(eval_details, f)

        # Update DB to point to mock file
        db_sub = db_session.query(Submission).filter(Submission.id == sub.id).first()
        db_sub.evaluation_output_path = temp_file
        db_session.commit()

        response = client.get(f"/evaluation/{sub.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["evaluation_output"] is not None
        assert data["evaluation_output"]["evaluation_mode"] == "AI_AUTONOMOUS"
        assert data["evaluation_output"]["questions"][0]["question_number"] == "1"

    def test_get_report_success(self, sample_data, tmp_path, db_session):
        """Verify GET /reports/{id} returns compiled JSON report details."""
        sub = sample_data["sub_completed"]

        # Mock evaluation output file required by ensure_report_artifacts
        eval_file = str(tmp_path / "eval_out.json")
        with open(eval_file, "w") as f:
            json.dump({"total_score": 92.5, "max_possible": 100.0, "questions": []}, f)

        # Mock report file on disk
        report_data = {
            "metadata": {"student_name": "Diana Prince"},
            "student_dashboard": {"summary": "Excellent work!"}
        }
        report_file = str(tmp_path / "report.json")
        with open(report_file, "w") as f:
            json.dump(report_data, f)

        # Mock PDF file (required to avoid regeneration)
        pdf_file = str(tmp_path / "report.pdf")
        with open(pdf_file, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"X" * 100000) # Mock minimum size > 50KB to pass validation

        # Update DB
        db_sub = db_session.query(Submission).filter(Submission.id == sub.id).first()
        db_sub.evaluation_output_path = eval_file
        db_sub.report_path = report_file
        db_session.commit()

        response = client.get(f"/reports/{sub.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["report"]["metadata"]["student_name"] == "Diana Prince"

    def test_get_class_analytics_success(self, sample_data):
        """Verify GET /analytics/class/{id} returns computed performance metrics."""
        exam_id = sample_data["exam"].id
        response = client.get(f"/analytics/class/{exam_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["exam_id"] == str(exam_id)
        assert data["exam_title"] == "Chemistry Midterm"
        assert data["total_submissions"] == 2
        assert data["completed_submissions"] == 1
        assert data["average_score"] == 92.5
        assert data["pass_rate"] == 100.0
        assert data["score_distribution"]["90-100"] == 1
        assert len(data["student_scores"]) == 1
        assert data["student_scores"][0]["student_name"] == "Diana Prince"

"""
GradeMIND Teacher Dashboard & Evaluation Monitoring Test Suite.
Tests dashboard overview, exam analytics, submission reviews, PDF download, and monitoring metrics.
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
from app.services.dashboard_service import DashboardService
from tests.conftest import engine, TestingSessionLocal

client = TestClient(app)


# ────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────

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
    """Provide a constant UUID for the test teacher."""
    return uuid4()


@pytest.fixture(autouse=True)
def mock_auth(test_teacher_id):
    """Automatically mock teacher authentication for dashboard tests."""
    from app.api.auth_deps import get_current_user, require_teacher_or_admin
    app.dependency_overrides[get_current_user] = lambda: {"id": test_teacher_id, "role": "TEACHER", "email": "teacher@test.com"}
    app.dependency_overrides[require_teacher_or_admin] = lambda: {"id": test_teacher_id, "role": "TEACHER", "email": "teacher@test.com"}
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db_session, test_teacher_id):
    """Create sample exams and submissions for the dashboard test."""
    # Create Exam 1
    exam1 = Exam(
        id=uuid4(),
        teacher_id=test_teacher_id,
        title="Mathematics Midterm",
        subject="Math",
        total_marks=100
    )
    db_session.add(exam1)

    # Create Exam 2
    exam2 = Exam(
        id=uuid4(),
        teacher_id=test_teacher_id,
        title="Physics Final",
        subject="Physics",
        total_marks=50
    )
    db_session.add(exam2)
    db_session.commit()

    # Create Submissions for Exam 1
    sub1 = Submission(
        id=uuid4(),
        exam_id=exam1.id,
        student_name="Alice Smith",
        student_roll_number="MATH-001",
        answer_sheet_path="mock_math1.png",
        ocr_status="COMPLETED",
        evaluation_status="COMPLETED",
        status=SubmissionStatus.COMPLETED,
        obtained_marks=85.0,
        total_marks=100.0,
        evaluation_confidence=0.92,
        evaluation_output_path="mock_math1_eval.json",
        report_path="mock_math1_report.json"
    )
    db_session.add(sub1)

    sub2 = Submission(
        id=uuid4(),
        exam_id=exam1.id,
        student_name="Bob Jones",
        student_roll_number="MATH-002",
        answer_sheet_path="mock_math2.png",
        ocr_status="COMPLETED",
        evaluation_status="COMPLETED",
        status=SubmissionStatus.COMPLETED,
        obtained_marks=60.0,
        total_marks=100.0,
        evaluation_confidence=0.78,
        evaluation_output_path="mock_math2_eval.json",
        report_path="mock_math2_report.json"
    )
    db_session.add(sub2)

    sub_pending = Submission(
        id=uuid4(),
        exam_id=exam1.id,
        student_name="Charlie Brown",
        student_roll_number="MATH-003",
        answer_sheet_path="mock_math3.png",
        ocr_status="PROCESSING",
        evaluation_status="PENDING",
        status=SubmissionStatus.PROCESSING
    )
    db_session.add(sub_pending)

    db_session.commit()

    return {
        "exam1": exam1,
        "exam2": exam2,
        "sub1": sub1,
        "sub2": sub2,
        "sub_pending": sub_pending
    }


# ────────────────────────────────────────────
# Test Cases
# ────────────────────────────────────────────

class TestDashboardAPIs:
    """Validates the dashboard endpoints and services."""

    def test_dashboard_overview(self, sample_data):
        """Verify GET /dashboard/overview calculates metrics correctly."""
        response = client.get("/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        
        # 2 exams created
        assert data["total_exams"] == 2
        # 3 submissions total for math midterm
        assert data["total_submissions"] == 3
        # 2 evaluated completed submissions
        assert data["evaluated_submissions"] == 2
        # Average score (85 + 60) / 2 = 72.5
        assert data["average_score"] == 72.5
        # Average confidence (0.92 + 0.78) / 2 = 0.85
        assert data["average_confidence"] == 0.85

    def test_exam_analytics_success(self, sample_data):
        """Verify GET /dashboard/exams/{exam_id} returns correct analytics."""
        exam_id = sample_data["exam1"].id
        response = client.get(f"/dashboard/exams/{exam_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["exam_id"] == str(exam_id)
        assert data["title"] == "Mathematics Midterm"
        assert data["submission_count"] == 3
        assert data["average_score"] == 72.5
        assert data["top_score"] == 85.0
        assert data["lowest_score"] == 60.0
        # 2 completed out of 3 = 66.67%
        assert data["completion_rate"] == 66.67

    def test_exam_analytics_not_found(self):
        """Verify GET /dashboard/exams/{exam_id} returns 404 for nonexistent exams."""
        nonexistent_id = uuid4()
        response = client.get(f"/dashboard/exams/{nonexistent_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_submission_review_fallback(self, sample_data):
        """Verify GET /dashboard/submissions/{submission_id} returns fallback breakdown if JSON file is missing."""
        sub_id = sample_data["sub1"].id
        response = client.get(f"/dashboard/submissions/{sub_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["student"] == "Alice Smith"
        assert data["score"] == 85.0
        assert data["confidence"] == 0.92
        assert len(data["question_breakdown"]) == 1
        assert data["question_breakdown"][0]["score_awarded"] == 85.0
        assert data["feedback"]["summary"] == ""

    def test_submission_review_with_file(self, sample_data, tmp_path):
        """Verify GET /dashboard/submissions/{submission_id} successfully parses evaluation output files."""
        sub1 = sample_data["sub1"]
        
        # Write mock evaluation output file
        eval_data = {
            "submission_id": 101,
            "total_score": 85.0,
            "max_possible": 100.0,
            "confidence_score": 0.92,
            "fairness_score": 0.95,
            "fairness_verified": True,
            "summary": "Overall excellent performance.",
            "strengths": ["Clear proofs", "Accurate equations"],
            "weaknesses": ["Minor arithmetic slip on Q2"],
            "improvements": ["Review decimal operations"],
            "questions": [
                {
                    "question_number": 1,
                    "max_marks": 50.0,
                    "score_awarded": 50.0,
                    "student_answer_extracted": "x = 5",
                    "criteria_feedback": "Perfect formula application.",
                    "confidence": 0.95
                },
                {
                    "question_number": 2,
                    "max_marks": 50.0,
                    "score_awarded": 35.0,
                    "student_answer_extracted": "y = 12 (should be 10)",
                    "criteria_feedback": "Calculation error near step 3.",
                    "confidence": 0.89
                }
            ]
        }
        
        # Override file path with a temp file path to make it real
        temp_file = str(tmp_path / "mock_math1_eval.json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(eval_data, f)
            
        sub1.evaluation_output_path = temp_file
        
        response = client.get(f"/dashboard/submissions/{sub1.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["student"] == "Alice Smith"
        assert data["score"] == 85.0
        assert data["confidence"] == 0.92
        assert len(data["question_breakdown"]) == 2
        assert data["question_breakdown"][0]["question_number"] == 1
        assert data["question_breakdown"][0]["score_awarded"] == 50.0
        assert data["question_breakdown"][1]["score_awarded"] == 35.0
        assert data["feedback"]["summary"] == "Overall excellent performance."
        assert "Clear proofs" in data["feedback"]["strengths"]
        assert len(data["fairness_checks"]) == 1
        assert data["fairness_checks"][0]["value"] == 0.95
        assert data["fairness_checks"][0]["status"] == "PASSED"

    def test_report_download_success(self, sample_data, tmp_path):
        """Verify GET /dashboard/submissions/{submission_id}/pdf serves compiled PDF file."""
        sub1 = sample_data["sub1"]
        
        # Create temp JSON report and PDF file
        temp_json = str(tmp_path / "mock_report.json")
        temp_pdf = str(tmp_path / "mock_report.pdf")
        
        with open(temp_json, "w") as f:
            f.write("{}")
            
        with open(temp_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%mock pdf content")
            
        sub1.report_path = temp_json
        
        response = client.get(f"/dashboard/submissions/{sub1.id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4" in response.content

    def test_report_download_missing_report(self, sample_data):
        """Verify GET /dashboard/submissions/{submission_id}/pdf returns 400 if report path is not set."""
        sub_pending = sample_data["sub_pending"]
        response = client.get(f"/dashboard/submissions/{sub_pending.id}/pdf")
        assert response.status_code == 400
        assert "has not been generated" in response.json()["detail"]

    def test_report_download_file_missing_on_disk(self, sample_data):
        """Verify GET /dashboard/submissions/{submission_id}/pdf returns 404 if PDF file is not on disk."""
        sub1 = sample_data["sub1"]
        sub1.report_path = "non_existent_report_path.json"
        
        response = client.get(f"/dashboard/submissions/{sub1.id}/pdf")
        assert response.status_code == 404
        assert "missing" in response.json()["detail"].lower()

    def test_monitoring_stats(self, sample_data, tmp_path):
        """Verify GET /dashboard/monitoring returns correct distributions and metrics."""
        sub1 = sample_data["sub1"]
        sub2 = sample_data["sub2"]
        
        # Setup mock eval files to verify distributions
        eval1 = {"fairness_score": 0.98, "fairness_verified": True}
        eval2 = {"fairness_score": 0.80, "fairness_verified": False}
        
        temp_file1 = str(tmp_path / "eval1.json")
        temp_file2 = str(tmp_path / "eval2.json")
        
        with open(temp_file1, "w") as f:
            json.dump(eval1, f)
        with open(temp_file2, "w") as f:
            json.dump(eval2, f)
            
        sub1.evaluation_output_path = temp_file1
        sub2.evaluation_output_path = temp_file2
        
        response = client.get("/dashboard/monitoring")
        assert response.status_code == 200
        data = response.json()
        
        # Check aggregate analytics
        assert data["aggregate_analytics"]["total_submissions"] == 3
        assert data["aggregate_analytics"]["completed_submissions"] == 2
        assert data["aggregate_analytics"]["failed_submissions"] == 0
        assert data["aggregate_analytics"]["average_score"] == 72.5

        # Check score distribution
        # sub1: 85% -> 80-89 bracket
        # sub2: 60% -> 60-69 bracket
        assert data["score_distribution"]["80-89"] == 1
        assert data["score_distribution"]["60-69"] == 1

        # Check confidence distribution
        # sub1: 0.92 -> high_confidence_85_plus
        # sub2: 0.78 -> medium_confidence_70_84
        assert data["confidence_distribution"]["high_confidence_85_plus"] == 1
        assert data["confidence_distribution"]["medium_confidence_70_84"] == 1

        # Check fairness metrics
        # avg = (0.98 + 0.80) / 2 = 0.89
        assert data["fairness_metrics"]["average_fairness_score"] == 0.89
        # 1 of 2 is flagged
        assert data["fairness_metrics"]["flagged_submissions_count"] == 1
        assert data["fairness_metrics"]["bias_free_rate"] == 50.0

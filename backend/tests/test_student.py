"""
GradeMIND Student Portal & Result Publishing Test Suite.
Verifies role-based access control, publishing/unpublishing flows, student result isolation,
unauthorized publication attempts, and secure PDF delivery.
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
from tests.conftest import engine, TestingSessionLocal, override_get_db

client = TestClient(app)


def clear_auth_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db


# ────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Reset database tables before each test function."""
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
    return uuid4()


@pytest.fixture
def test_student_a_id():
    return uuid4()


@pytest.fixture
def test_student_b_id():
    return uuid4()


@pytest.fixture
def sample_data(db_session, test_teacher_id):
    """Create sample exam and submissions for Student A and Student B."""
    # Create Exam
    exam = Exam(
        id=uuid4(),
        teacher_id=test_teacher_id,
        title="Chemistry Quiz 1",
        subject="Chemistry",
        total_marks=100,
        results_published=False  # Start unpublished
    )
    db_session.add(exam)
    db_session.commit()

    # Student A Submission
    sub_a = Submission(
        id=uuid4(),
        exam_id=exam.id,
        student_name="Student Alpha",
        student_roll_number="CHEM-A",
        status=SubmissionStatus.COMPLETED,
        obtained_marks=92.0,
        total_marks=100.0,
        evaluation_confidence=0.96,
        evaluation_output_path="mock_chem_a.json",
        report_path="mock_chem_a.json"
    )
    db_session.add(sub_a)

    # Student B Submission
    sub_b = Submission(
        id=uuid4(),
        exam_id=exam.id,
        student_name="Student Beta",
        student_roll_number="CHEM-B",
        status=SubmissionStatus.COMPLETED,
        obtained_marks=75.0,
        total_marks=100.0,
        evaluation_confidence=0.88,
        evaluation_output_path="mock_chem_b.json",
        report_path="mock_chem_b.json"
    )
    db_session.add(sub_b)

    db_session.commit()

    return {
        "exam": exam,
        "sub_a": sub_a,
        "sub_b": sub_b
    }


# ────────────────────────────────────────────
# Test Cases
# ────────────────────────────────────────────

class TestStudentPortal:

    def test_student_unauthorized_access(self):
        """Verify that requests without credentials return 401."""
        response = client.get("/student/results")
        assert response.status_code == 401

    def test_student_access_denied_before_publication(self, sample_data, test_student_a_id):
        """Verify students get 403 Forbidden when accessing results before publication."""
        from app.api.auth_deps import get_current_user
        # Mock login as Student Alpha
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_student_a_id,
            "name": "Student Alpha",
            "email": "alpha@student.com",
            "role": "STUDENT"
        }

        # Overview should return 0 reports since the exam is not published
        response = client.get("/student/results")
        assert response.status_code == 200
        data = response.json()
        assert data["total_exams"] == 0
        assert len(data["reports"]) == 0

        # Accessing own submission details directly should return 403
        sub_a_id = sample_data["sub_a"].id
        detail_response = client.get(f"/student/results/{sub_a_id}")
        assert detail_response.status_code == 403
        assert "not been published" in detail_response.json()["detail"].lower()

        # Accessing PDF before publication should return 403
        pdf_response = client.get(f"/student/results/{sub_a_id}/pdf")
        assert pdf_response.status_code == 403

        clear_auth_overrides()

    def test_teacher_publish_flow_and_student_access(self, sample_data, test_teacher_id, test_student_a_id, test_student_b_id, tmp_path):
        """Verify complete publish/unpublish workflow and access controls."""
        from app.api.auth_deps import get_current_user, require_teacher_or_admin

        # 1. Student A tries to publish -> should be rejected with 403 (needs teacher or admin)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_student_a_id,
            "name": "Student Alpha",
            "email": "alpha@student.com",
            "role": "STUDENT"
        }
        app.dependency_overrides[require_teacher_or_admin] = lambda: {
            "id": test_student_a_id,
            "name": "Student Alpha",
            "email": "alpha@student.com",
            "role": "STUDENT"
        }
        
        exam_id = sample_data["exam"].id
        pub_response = client.post(f"/results/publish/{exam_id}")
        assert pub_response.status_code == 403

        # Clear override
        clear_auth_overrides()

        # 2. Log in as Teacher to publish the exam
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_teacher_id,
            "name": "Teacher Jones",
            "email": "jones@teacher.com",
            "role": "TEACHER"
        }
        app.dependency_overrides[require_teacher_or_admin] = lambda: {
            "id": test_teacher_id,
            "name": "Teacher Jones",
            "email": "jones@teacher.com",
            "role": "TEACHER"
        }

        pub_response = client.post(f"/results/publish/{exam_id}")
        assert pub_response.status_code == 200
        assert pub_response.json()["results_published"] is True

        clear_auth_overrides()

        # 3. Log in as Student A (Student Alpha) to access published results
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_student_a_id,
            "name": "Student Alpha",
            "email": "alpha@student.com",
            "role": "STUDENT"
        }

        # Overview should now include the published exam
        response = client.get("/student/results")
        assert response.status_code == 200
        data = response.json()
        assert data["total_exams"] == 1
        assert data["average_score"] == 92.0
        assert data["reports"][0]["exam_title"] == "Chemistry Quiz 1"

        # Accessing own submission details should succeed
        sub_a_id = sample_data["sub_a"].id
        detail_response = client.get(f"/student/results/{sub_a_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["score"] == 92.0

        # Attempt to access Student B's submission -> should return 403 Forbidden
        sub_b_id = sample_data["sub_b"].id
        cross_response = client.get(f"/student/results/{sub_b_id}")
        assert cross_response.status_code == 403
        assert "access" in cross_response.json()["detail"].lower()

        # Test PDF retrieval when file is missing on storage
        pdf_missing_response = client.get(f"/student/results/{sub_a_id}/pdf")
        assert pdf_missing_response.status_code == 404
        assert "missing" in pdf_missing_response.json()["detail"].lower()

        # Mock mock_chem_a.pdf on disk to test successful PDF download
        temp_pdf = str(tmp_path / "mock_chem_a.pdf")
        with open(temp_pdf, "wb") as f:
            f.write(b"%PDF-1.4\nmock chemistry pdf")
        
        # Override report path in database
        db = TestingSessionLocal()
        sub_db = db.query(Submission).filter(Submission.id == sub_a_id).first()
        sub_db.report_path = temp_pdf
        db.commit()
        db.close()

        pdf_success_response = client.get(f"/student/results/{sub_a_id}/pdf")
        assert pdf_success_response.status_code == 200
        assert pdf_success_response.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4" in pdf_success_response.content

        clear_auth_overrides()

        # 4. Log in as Teacher to unpublish
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_teacher_id,
            "name": "Teacher Jones",
            "email": "jones@teacher.com",
            "role": "TEACHER"
        }
        app.dependency_overrides[require_teacher_or_admin] = lambda: {
            "id": test_teacher_id,
            "name": "Teacher Jones",
            "email": "jones@teacher.com",
            "role": "TEACHER"
        }

        unpub_response = client.post(f"/results/unpublish/{exam_id}")
        assert unpub_response.status_code == 200
        assert unpub_response.json()["results_published"] is False

        clear_auth_overrides()

        # 5. Log in as Student A again -> access should now be blocked (403)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": test_student_a_id,
            "name": "Student Alpha",
            "email": "alpha@student.com",
            "role": "STUDENT"
        }

        response = client.get("/student/results")
        assert response.json()["total_exams"] == 0

        detail_response = client.get(f"/student/results/{sub_a_id}")
        assert detail_response.status_code == 403

        clear_auth_overrides()

"""
GradeMIND Submission API Test Suite.
Integration tests for the Submission Management System endpoints.
Tests upload, file validation, status updates, OCR triggers, authorization, and database operations.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4, UUID

from app.core.database import Base
from app.main import app
from app.db.session import get_db
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from tests.conftest import engine, TestingSessionLocal



# ────────────────────────────────────────────
# Auth Mock Helpers
# ────────────────────────────────────────────

def mock_teacher_auth(user_id=None):
    """Mock authentication as a TEACHER user."""
    if user_id is None:
        user_id = uuid4()

    def override_get_current_user():
        return {"id": user_id, "role": "TEACHER", "email": "teacher@test.com"}

    def override_require_teacher_or_admin():
        return override_get_current_user()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_teacher_or_admin] = override_require_teacher_or_admin
    return user_id


def mock_admin_auth(user_id=None):
    """Mock authentication as an ADMIN user."""
    if user_id is None:
        user_id = uuid4()

    def override_get_current_user():
        return {"id": user_id, "role": "ADMIN", "email": "admin@test.com"}

    def override_require_teacher_or_admin():
        return override_get_current_user()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_teacher_or_admin] = override_require_teacher_or_admin
    return user_id


def mock_student_auth(user_id=None):
    """Mock authentication as a STUDENT user — should be rejected by require_teacher_or_admin."""
    if user_id is None:
        user_id = uuid4()

    def override_get_current_user():
        return {"id": user_id, "role": "STUDENT", "email": "student@test.com"}

    def override_require_teacher_or_admin():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not enough permissions")

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_teacher_or_admin] = override_require_teacher_or_admin
    return user_id


# ────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create and tear down all tables for each test."""
    print("Base.metadata.tables.keys():", Base.metadata.tables.keys())
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
    """Create a sample exam in the database for submission tests."""
    teacher_id = uuid4()
    exam = Exam(
        teacher_id=teacher_id,
        title="Midterm Physics",
        subject="Physics",
        total_marks=100,
        question_paper_url="mock_paper.pdf"
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def sample_pdf():
    """Generate a minimal valid PDF file content for upload testing."""
    # Minimal PDF structure (valid enough for file-type checking)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    return pdf_content


client = TestClient(app)


# ────────────────────────────────────────────
# Upload Tests
# ────────────────────────────────────────────

class TestUploadSubmission:
    """Tests for POST /submissions/upload"""

    def test_upload_valid_pdf(self, sample_exam, sample_pdf):
        """A teacher can upload a valid PDF submission."""
        mock_teacher_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Aarav Sharma",
                "student_roll_number": "CS2024001",
            },
            files={"file": ("answer_sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["student_name"] == "Aarav Sharma"
        assert data["student_roll_number"] == "CS2024001"
        assert data["status"] == SubmissionStatus.UPLOADED
        assert data["exam_id"] == str(sample_exam.id)
        assert data["total_marks"] == 100.0

    def test_upload_valid_png(self, sample_exam):
        """A teacher can upload a valid PNG submission."""
        mock_teacher_auth()

        # Minimal PNG bytes (1x1 white pixel)
        png_content = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Priya Patel",
                "student_roll_number": "CS2024002",
            },
            files={"file": ("answer.png", io.BytesIO(png_content), "image/png")},
        )

        assert response.status_code == 201
        assert response.json()["student_name"] == "Priya Patel"

    def test_upload_admin_allowed(self, sample_exam, sample_pdf):
        """An admin can also upload submissions."""
        mock_admin_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Admin Upload Test",
                "student_roll_number": "CS2024003",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 201


class TestFileValidation:
    """Tests for file type and size validation."""

    def test_reject_invalid_file_type(self, sample_exam):
        """Reject upload of unsupported file types (e.g., .txt)."""
        mock_teacher_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Test Student",
                "student_roll_number": "CS2024004",
            },
            files={"file": ("notes.txt", io.BytesIO(b"plain text content"), "text/plain")},
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_reject_docx_file(self, sample_exam):
        """Reject .docx uploads."""
        mock_teacher_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Test Student",
                "student_roll_number": "CS2024005",
            },
            files={"file": ("answer.docx", io.BytesIO(b"fake docx"), "application/vnd.openxmlformats")},
        )

        assert response.status_code == 400

    def test_reject_nonexistent_exam(self, sample_pdf):
        """Reject upload for a non-existent exam ID."""
        mock_teacher_auth()
        fake_exam_id = uuid4()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(fake_exam_id),
                "student_name": "Test Student",
                "student_roll_number": "CS2024006",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()

    def test_reject_oversized_file(self, sample_exam):
        """Reject upload of files larger than 20MB."""
        mock_teacher_auth()
        # Create a mock file payload slightly over 20MB
        oversized_content = b"0" * (20 * 1024 * 1024 + 1)

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Too Big",
                "student_roll_number": "CS2024007",
            },
            files={"file": ("large.pdf", io.BytesIO(oversized_content), "application/pdf")},
        )

        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()


class TestAuthorization:
    """Tests for role-based access control."""

    def test_student_cannot_upload(self, sample_exam, sample_pdf):
        """Students should be rejected from uploading submissions."""
        mock_student_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Student Self",
                "student_roll_number": "CS2024007",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        assert response.status_code == 403

    def test_student_cannot_list(self):
        """Students should be rejected from listing submissions."""
        mock_student_auth()

        response = client.get("/submissions")
        assert response.status_code == 403

    def test_student_cannot_delete(self, sample_exam, sample_pdf):
        """Students should not be able to delete submissions."""
        mock_student_auth()

        response = client.delete(f"/submissions/{uuid4()}")
        assert response.status_code == 403


class TestListAndGetSubmissions:
    """Tests for GET endpoints."""

    def _create_submission(self, exam_id, sample_pdf, roll="CS001", name="Test"):
        """Helper to create a submission via the API."""
        mock_teacher_auth()
        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(exam_id),
                "student_name": name,
                "student_roll_number": roll,
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )
        assert response.status_code == 201
        return response.json()

    def test_list_submissions(self, sample_exam, sample_pdf):
        """List submissions returns created records."""
        self._create_submission(sample_exam.id, sample_pdf, "CS001")
        self._create_submission(sample_exam.id, sample_pdf, "CS002")

        mock_teacher_auth()
        response = client.get("/submissions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["submissions"]) >= 2

    def test_list_submissions_filter_by_exam(self, sample_exam, sample_pdf):
        """List submissions filtered by exam_id."""
        self._create_submission(sample_exam.id, sample_pdf, "CS003")

        mock_teacher_auth()
        response = client.get(f"/submissions?exam_id={sample_exam.id}")

        assert response.status_code == 200
        for sub in response.json()["submissions"]:
            assert sub["exam_id"] == str(sample_exam.id)

    def test_get_single_submission(self, sample_exam, sample_pdf):
        """Get a single submission by ID."""
        created = self._create_submission(sample_exam.id, sample_pdf, "CS004")

        mock_teacher_auth()
        response = client.get(f"/submissions/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["student_roll_number"] == "CS004"

    def test_get_nonexistent_submission(self):
        """Return 404 for a non-existent submission ID."""
        mock_teacher_auth()
        response = client.get(f"/submissions/{uuid4()}")
        assert response.status_code == 404


class TestStatusEndpoint:
    """Tests for GET /submissions/{id}/status"""

    def test_get_status(self, sample_exam, sample_pdf, db_session):
        """Check status of an uploaded submission."""
        mock_teacher_auth()

        upload_response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Status Test",
                "student_roll_number": "CS005",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )
        submission_id = upload_response.json()["id"]

        response = client.get(f"/submissions/{submission_id}/status")
        assert response.status_code == 200
        assert response.json()["id"] == submission_id
        assert "status" in response.json()


class TestDeleteSubmission:
    """Tests for DELETE /submissions/{id}"""

    def test_delete_existing_submission(self, sample_exam, sample_pdf):
        """Delete an existing submission."""
        mock_teacher_auth()

        upload_response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Delete Test",
                "student_roll_number": "CS006",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )
        submission_id = upload_response.json()["id"]

        response = client.delete(f"/submissions/{submission_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = client.get(f"/submissions/{submission_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_submission(self):
        """Return 404 when deleting a non-existent submission."""
        mock_teacher_auth()
        response = client.delete(f"/submissions/{uuid4()}")
        assert response.status_code == 404


class TestDatabaseOperations:
    """Tests for direct database integrity."""

    def test_submission_exam_relationship(self, sample_exam, sample_pdf, db_session):
        """Verify the submission correctly references the exam."""
        mock_teacher_auth()

        upload_response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Relationship Test",
                "student_roll_number": "CS007",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        submission_id = upload_response.json()["id"]

        # Query directly from DB
        submission = db_session.query(Submission).filter(
            Submission.id == UUID(submission_id)
        ).first()

        assert submission is not None
        assert submission.exam_id == sample_exam.id
        assert submission.total_marks == 100.0

    def test_status_defaults(self, sample_exam, sample_pdf):
        """Verify default status values on creation."""
        mock_teacher_auth()

        response = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(sample_exam.id),
                "student_name": "Default Status Test",
                "student_roll_number": "CS008",
            },
            files={"file": ("sheet.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        )

        data = response.json()
        assert data["status"] == "UPLOADED"
        assert data["ocr_status"] is None
        assert data["evaluation_status"] is None
        assert data["obtained_marks"] is None
        assert data["ocr_confidence"] is None
        assert data["evaluation_confidence"] is None

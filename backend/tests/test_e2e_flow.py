"""
GradeMIND End-to-End User Journey Test.

Exercises the real user journey through actual HTTP endpoints, with role
transitions, and — unlike test_pipeline_integration.py (which calls
SubmissionService.process_submission() directly) — through the real
FastAPI BackgroundTasks path triggered by POST /submissions/upload:

    create exam (Teacher) -> upload answer sheet w/ mocked OCR (Teacher,
    real background processing) -> fetch result (Teacher) -> student is
    denied before publish -> publish (Teacher) -> student fetches their
    own published result -> another student is denied access.

Also exercises role guard enforcement end-to-end: a STUDENT cannot create
an exam or publish results.
"""

import io
from uuid import uuid4, UUID

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base
from app.main import app
from app.db.session import get_db
from app.models.submission import SubmissionStatus
from app.api.auth_deps import get_current_user, require_teacher_or_admin
from tests.conftest import engine, TestingSessionLocal, override_get_db

client = TestClient(app)


def _clear_auth_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db


def _login_as(role: str, user_id, name: str, email: str):
    """Override auth dependencies to simulate a logged-in user of a given role."""
    user = {"id": str(user_id), "name": name, "email": email, "role": role}
    app.dependency_overrides[get_current_user] = lambda: user
    if role in ("TEACHER", "ADMIN"):
        app.dependency_overrides[require_teacher_or_admin] = lambda: user
    return user


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Reset database tables before each test function."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    _clear_auth_overrides()


@pytest.fixture
def sample_answer_sheet() -> bytes:
    """Minimal valid 1x1 white pixel PNG (accepted by upload validation)."""
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _mock_ocr(monkeypatch, text: str) -> None:
    """Patch OCRManager.extract_text so the real background pipeline never
    touches a real OCR engine, while still exercising every other stage
    (segment -> evaluate -> persist -> report) for real."""
    from AI.schemas.ocr_schema import OCRDocument, OCRLine
    from AI.ocr.ocr_manager import OCRManager

    def mock_extract_text(self, image_path, submission_id):
        return OCRDocument(
            submission_id=str(submission_id),
            confidence=0.93,
            lines=[OCRLine(text=text, confidence=0.93, bounding_box=[])],
            regions=[],
        )

    monkeypatch.setattr(OCRManager, "extract_text", mock_extract_text)


class TestEndToEndUserJourney:
    def test_full_journey_create_upload_evaluate_publish_student_fetch(
        self, sample_answer_sheet, tmp_path, monkeypatch
    ):
        teacher_id = uuid4()
        student_id = uuid4()
        other_student_id = uuid4()

        # ── Role guard: a STUDENT cannot create an exam ────────────────────
        _login_as("STUDENT", student_id, "Journey Student", "journey.student@test.com")
        denied = client.post(
            "/exams", json={"title": "Physics Midterm", "subject": "Physics", "total_marks": 20}
        )
        assert denied.status_code == 403
        _clear_auth_overrides()

        # ── 1. Teacher creates the exam ─────────────────────────────────────
        _login_as("TEACHER", teacher_id, "Teacher E2E", "teacher.e2e@test.com")
        exam_resp = client.post(
            "/exams", json={"title": "Physics Midterm", "subject": "Physics", "total_marks": 20}
        )
        assert exam_resp.status_code == 200, exam_resp.text
        exam_id = UUID(exam_resp.json()["id"])
        assert exam_resp.json()["status"] == "PENDING"

        # Configure the question paper directly (question-paper upload has its
        # own dedicated, separately-tested endpoint; here we exercise the
        # answer-sheet pipeline).
        question_paper_path = tmp_path / "question_paper.txt"
        question_paper_path.write_text("Q1. Explain Newton's second law of motion. [20 Marks]", encoding="utf-8")
        db = TestingSessionLocal()
        from app.models.exam import Exam
        exam_row = db.query(Exam).filter(Exam.id == exam_id).first()
        exam_row.question_paper_url = str(question_paper_path)
        db.commit()
        db.close()

        # ── 2. Teacher uploads the answer sheet; real background pipeline
        #      (OCR -> segment -> evaluate -> persist -> report) runs, not
        #      bypassed via a direct process_submission() call. ─────────────
        _mock_ocr(
            monkeypatch,
            "Q1. Newton's second law states that force equals mass times acceleration, F = ma.",
        )
        upload_resp = client.post(
            "/submissions/upload",
            data={
                "exam_id": str(exam_id),
                "student_name": "Journey Student",
                "student_roll_number": "E2E-001",
            },
            files={"file": ("answers.png", io.BytesIO(sample_answer_sheet), "image/png")},
        )
        assert upload_resp.status_code == 201, upload_resp.text
        submission_id = UUID(upload_resp.json()["id"])
        # Response returns immediately, before background processing finishes.
        assert upload_resp.json()["status"] == SubmissionStatus.UPLOADED

        # ── 3. Teacher fetches the result: background processing has already
        #      completed by the time TestClient returns (Starlette runs
        #      BackgroundTasks before the request context tears down). ──────
        status_resp = client.get(f"/submissions/{submission_id}/status")
        assert status_resp.status_code == 200
        status_body = status_resp.json()
        assert status_body["status"] == SubmissionStatus.COMPLETED
        assert status_body["ocr_status"] == "COMPLETED"
        assert status_body["evaluation_status"] == "COMPLETED"
        assert status_body["error_message"] in (None, "")
        assert status_body["obtained_marks"] is not None
        assert status_body["obtained_marks"] > 0

        detail_resp = client.get(f"/submissions/{submission_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["evaluation_output_path"] is not None
        assert detail_resp.json()["report_path"] is not None

        _clear_auth_overrides()

        # ── 4. Before publishing, the student cannot see the result ────────
        _login_as("STUDENT", student_id, "Journey Student", "journey.student@test.com")
        pre_publish = client.get(f"/student/results/{submission_id}")
        assert pre_publish.status_code == 403
        assert "not been published" in pre_publish.json()["detail"].lower()
        _clear_auth_overrides()

        # ── 5. A STUDENT cannot publish results ─────────────────────────────
        _login_as("STUDENT", student_id, "Journey Student", "journey.student@test.com")
        student_publish_attempt = client.post(f"/results/publish/{exam_id}")
        assert student_publish_attempt.status_code == 403
        _clear_auth_overrides()

        # ── 6. Teacher publishes the exam's results ─────────────────────────
        _login_as("TEACHER", teacher_id, "Teacher E2E", "teacher.e2e@test.com")
        publish_resp = client.post(f"/results/publish/{exam_id}")
        assert publish_resp.status_code == 200
        assert publish_resp.json()["results_published"] is True
        _clear_auth_overrides()

        # ── 7. The owning student now fetches their published result ───────
        _login_as("STUDENT", student_id, "Journey Student", "journey.student@test.com")
        overview_resp = client.get("/student/results")
        assert overview_resp.status_code == 200
        overview = overview_resp.json()
        assert overview["total_exams"] == 1
        assert overview["reports"][0]["exam_title"] == "Physics Midterm"

        review_resp = client.get(f"/student/results/{submission_id}")
        assert review_resp.status_code == 200
        review = review_resp.json()
        assert review["score"] == status_body["obtained_marks"]
        assert review["submission_id"] == str(submission_id)
        _clear_auth_overrides()

        # ── 8. A different student cannot access this submission's result ──
        _login_as("STUDENT", other_student_id, "Another Student", "another.student@test.com")
        cross_access = client.get(f"/student/results/{submission_id}")
        assert cross_access.status_code == 403
        assert "access" in cross_access.json()["detail"].lower()
        _clear_auth_overrides()

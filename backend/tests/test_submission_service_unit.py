"""
Unit tests for SubmissionService targeting behavior not already exercised by
the API-level tests (test_submissions.py) or the full-pipeline integration
tests (test_pipeline_integration.py, test_e2e_flow.py): failure paths,
status-message accuracy, report-artifact regeneration, and the score/
metadata-loading helpers.
"""

import json
import os
from uuid import uuid4

import pytest

from app.core.database import Base
from app.models.exam import Exam
from app.models.submission import Submission, SubmissionStatus
from app.services.submission_service import SubmissionService
from tests.conftest import engine, TestingSessionLocal


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def service(db):
    return SubmissionService(db)


@pytest.fixture
def exam(db):
    e = Exam(teacher_id=uuid4(), title="Unit Test Exam", subject="Biology", total_marks=50)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@pytest.fixture
def submission(db, exam):
    s = Submission(
        exam_id=exam.id,
        student_name="Coverage Student",
        student_roll_number="COV-001",
        status=SubmissionStatus.UPLOADED,
        total_marks=float(exam.total_marks),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ─────────────────────────────────────────────────────────────────────────
# _format_score / list_evaluated_reports
# ─────────────────────────────────────────────────────────────────────────

class TestFormatScore:
    def test_both_none(self, service):
        assert service._format_score(None, None) == "Not scored"

    def test_total_none(self, service):
        assert service._format_score(42.0, None) == "42"

    def test_obtained_none(self, service):
        assert service._format_score(None, 100.0) == "0/100"

    def test_both_present(self, service):
        assert service._format_score(85.5, 100.0) == "85.5/100"


class TestListEvaluatedReports:
    def test_only_completed_submissions_included(self, db, exam, submission):
        """UPLOADED submissions must not appear in the evaluated-reports list."""
        completed = Submission(
            exam_id=exam.id,
            student_name="Completed Student",
            student_roll_number="COV-002",
            status=SubmissionStatus.COMPLETED,
            obtained_marks=40.0,
            total_marks=50.0,
        )
        db.add(completed)
        db.commit()

        service = SubmissionService(db)
        reports = service.list_evaluated_reports()

        roll_numbers = {r["studentRollNumber"] for r in reports}
        assert "COV-002" in roll_numbers
        assert "COV-001" not in roll_numbers  # still UPLOADED, not COMPLETED

        report = next(r for r in reports if r["studentRollNumber"] == "COV-002")
        assert report["examTitle"] == "Unit Test Exam"
        assert report["score"] == "40/50"
        assert report["resultsUrl"] == f"/results?submissionId={completed.id}"


# ─────────────────────────────────────────────────────────────────────────
# Pipeline failure paths — status/error_message must accurately reflect
# which stage failed, and never silently leave the submission stuck.
# ─────────────────────────────────────────────────────────────────────────

class TestPipelineFailurePaths:
    def test_trigger_ocr_missing_answer_sheet_raises(self, service, db, exam):
        sub = Submission(
            exam_id=exam.id,
            student_name="No Sheet",
            student_roll_number="COV-003",
            status=SubmissionStatus.UPLOADED,
            answer_sheet_path=None,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        with pytest.raises(ValueError, match="no answer sheet"):
            service.trigger_ocr(sub.id)

    def test_trigger_ocr_engine_failure_marks_failed_with_real_error(self, service, submission, tmp_path, monkeypatch):
        """A genuine OCR engine failure should be recorded with its real message
        on the submission (not silently swallowed), and status must become FAILED."""
        sheet = tmp_path / "sheet.png"
        sheet.write_bytes(b"not a real image")
        submission.answer_sheet_path = str(sheet)
        service.db.commit()

        from AI.ocr.ocr_manager import OCRManager

        def boom(self, image_path, submission_id):
            raise RuntimeError("all OCR engines unavailable")

        monkeypatch.setattr(OCRManager, "extract_text", boom)

        with pytest.raises(RuntimeError):
            service.trigger_ocr(submission.id)

        updated = service.get_submission(submission.id)
        assert updated.status == SubmissionStatus.FAILED
        assert updated.ocr_status == "FAILED"
        assert "all OCR engines unavailable" in updated.error_message

    def test_trigger_evaluation_without_ocr_output_raises(self, service, submission):
        with pytest.raises(ValueError, match="no OCR output"):
            service.trigger_evaluation(submission.id)

    def test_process_submission_ocr_failure_uses_stage_neutral_message(
        self, service, submission, tmp_path, monkeypatch
    ):
        """
        Regression test: a failure during the OCR stage must not be reported
        to the frontend as "Evaluation could not be completed" — that message
        was misleading when the pipeline never reached evaluation at all.
        """
        sheet = tmp_path / "sheet.png"
        sheet.write_bytes(b"fake")
        submission.answer_sheet_path = str(sheet)
        service.db.commit()

        from AI.ocr.ocr_manager import OCRManager
        monkeypatch.setattr(
            OCRManager, "extract_text",
            lambda self, image_path, submission_id: (_ for _ in ()).throw(RuntimeError("engine down")),
        )

        service.process_submission(submission.id)

        updated = service.get_submission(submission.id)
        assert updated.status == SubmissionStatus.FAILED
        assert updated.error_message == "Processing could not be completed. Please retry the submission."
        assert "Evaluation" not in updated.error_message

    def test_generate_report_without_evaluation_output_raises(self, service, submission):
        with pytest.raises(ValueError, match="no evaluation output"):
            service.generate_report(submission.id)


# ─────────────────────────────────────────────────────────────────────────
# ensure_report_artifacts / _is_broken_pdf — report regeneration logic
# ─────────────────────────────────────────────────────────────────────────

class TestEnsureReportArtifacts:
    def test_missing_submission_raises(self, service):
        with pytest.raises(ValueError, match="SUBMISSION_NOT_FOUND"):
            service.ensure_report_artifacts(uuid4())

    def test_missing_evaluation_output_raises(self, service, submission):
        with pytest.raises(ValueError, match="EVALUATION_OUTPUT_MISSING"):
            service.ensure_report_artifacts(submission.id)

    def test_regenerates_when_pdf_missing(self, service, submission, tmp_path, monkeypatch):
        """If the JSON report exists but its PDF sibling is missing, regenerate."""
        eval_path = tmp_path / "eval.json"
        eval_path.write_text(json.dumps({
            "submission_id": str(submission.id),
            "total_score": 10.0,
            "max_possible": 50.0,
            "confidence_score": 0.8,
            "evaluation_mode": "AI_AUTONOMOUS",
            "questions": [],
            "fairness_verified": True,
            "fairness_score": 1.0,
            "strengths": [], "weaknesses": [], "improvements": [], "study_recommendations": [],
            "summary": "ok",
        }), encoding="utf-8")

        report_path = tmp_path / "report.json"
        report_path.write_text("{}", encoding="utf-8")  # exists, but no matching .pdf

        submission.evaluation_output_path = str(eval_path)
        submission.report_path = str(report_path)
        service.db.commit()

        regenerated = {"called": False}

        def fake_generate_report(self, submission_id):
            regenerated["called"] = True
            pdf_path = os.path.splitext(str(report_path))[0] + ".pdf"
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\nregenerated")

        monkeypatch.setattr(SubmissionService, "generate_report", fake_generate_report)

        result_report_path, result_pdf_path = service.ensure_report_artifacts(submission.id)
        assert regenerated["called"] is True
        assert os.path.exists(result_pdf_path)


class TestGenerateStudyPlanPdf:
    def test_uses_study_recommendations_when_present(self, service, submission, tmp_path):
        eval_path = tmp_path / "eval.json"
        eval_path.write_text(json.dumps({
            "submission_id": str(submission.id),
            "total_score": 30.0,
            "max_possible": 50.0,
            "confidence_score": 0.8,
            "evaluation_mode": "AI_AUTONOMOUS",
            "questions": [],
            "fairness_verified": True,
            "fairness_score": 1.0,
            "strengths": [],
            "weaknesses": ["Weak grasp of osmosis"],
            "improvements": ["Practice diffusion problems"],
            "study_recommendations": ["Cell Membrane Transport"],
            "summary": "ok",
        }), encoding="utf-8")

        report_path = tmp_path / "report.json"
        report_path.write_text("{}", encoding="utf-8")
        pdf_path = tmp_path / "report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n" + b"0" * 50)  # already valid, no regeneration needed

        submission.evaluation_output_path = str(eval_path)
        submission.report_path = str(report_path)
        service.db.commit()

        plan_path = service.generate_study_plan_pdf(submission.id)

        assert plan_path.endswith("_study_plan.pdf")
        assert os.path.exists(plan_path)
        assert os.path.getsize(plan_path) > 0

    def test_falls_back_to_default_topics_when_no_recommendations(self, service, submission, tmp_path):
        """When study_recommendations is empty, generic topics must be used
        instead of producing an empty/broken study plan."""
        eval_path = tmp_path / "eval.json"
        eval_path.write_text(json.dumps({
            "submission_id": str(submission.id),
            "total_score": 30.0,
            "max_possible": 50.0,
            "confidence_score": 0.8,
            "evaluation_mode": "AI_AUTONOMOUS",
            "questions": [],
            "fairness_verified": True,
            "fairness_score": 1.0,
            "strengths": [],
            "weaknesses": [],
            "improvements": [],
            "study_recommendations": [],
            "summary": "ok",
        }), encoding="utf-8")

        report_path = tmp_path / "report.json"
        report_path.write_text("{}", encoding="utf-8")
        pdf_path = tmp_path / "report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n" + b"0" * 50)

        submission.evaluation_output_path = str(eval_path)
        submission.report_path = str(report_path)
        service.db.commit()

        plan_path = service.generate_study_plan_pdf(submission.id)
        assert os.path.exists(plan_path)
        assert os.path.getsize(plan_path) > 0


class TestIsBrokenPdf:
    def test_nonexistent_file_is_broken(self, service):
        assert service._is_broken_pdf("/nonexistent/report.pdf") is True

    def test_none_path_is_broken(self, service):
        assert service._is_broken_pdf(None) is True

    def test_tiny_file_is_broken(self, service, tmp_path):
        p = tmp_path / "tiny.pdf"
        p.write_bytes(b"x")
        assert service._is_broken_pdf(str(p)) is True

    def test_stale_fallback_marker_is_broken(self, service, tmp_path):
        p = tmp_path / "stale.pdf"
        p.write_bytes(b"Install pdflatex to render this report properly" + b"0" * 20)
        assert service._is_broken_pdf(str(p)) is True

    def test_valid_pdf_is_not_broken(self, service, tmp_path):
        p = tmp_path / "valid.pdf"
        p.write_bytes(b"%PDF-1.4\n" + b"0" * 50)
        assert service._is_broken_pdf(str(p)) is False


# ─────────────────────────────────────────────────────────────────────────
# Answer-key / exam-context loading helpers
# ─────────────────────────────────────────────────────────────────────────

class TestLoadAnswerKeyMetadata:
    def test_no_answer_key_returns_none(self, service, submission):
        """Exams configured for autonomous evaluation must not fabricate answer-key metadata."""
        assert service._load_answer_key_metadata(submission) is None

    def test_unreadable_answer_key_path_raises(self, service, db, exam, submission):
        exam.answer_key_url = "/nonexistent/answer_key.txt"
        db.commit()
        with pytest.raises(ValueError, match="not readable"):
            service._load_answer_key_metadata(submission)

    def test_empty_answer_key_raises(self, service, db, exam, submission, tmp_path):
        answer_key = tmp_path / "answer_key.txt"
        answer_key.write_text("   ", encoding="utf-8")  # whitespace-only -> empty after strip
        exam.answer_key_url = str(answer_key)
        db.commit()
        with pytest.raises(ValueError, match="empty"):
            service._load_answer_key_metadata(submission)

    def test_valid_answer_key_and_question_paper_builds_metadata(self, service, db, exam, submission, tmp_path):
        question_paper = tmp_path / "questions.txt"
        question_paper.write_text("Q1. Explain gravity. [50 Marks]", encoding="utf-8")
        answer_key = tmp_path / "answer_key.txt"
        answer_key.write_text("Gravity is the force of attraction between masses.", encoding="utf-8")

        exam.question_paper_url = str(question_paper)
        exam.answer_key_url = str(answer_key)
        db.commit()

        metadata = service._load_answer_key_metadata(submission)
        assert metadata is not None
        assert "question_1" in metadata
        assert "gravity" in metadata["question_1"]["answer_key"].lower()


class TestLoadExamContext:
    def test_missing_question_paper_raises(self, service, submission):
        with pytest.raises(ValueError, match="no uploaded question paper"):
            service._load_exam_context(submission)

    def test_valid_question_paper_builds_autonomous_context(self, service, db, exam, submission, tmp_path):
        question_paper = tmp_path / "questions.txt"
        question_paper.write_text("Q1. Explain gravity. [50 Marks]", encoding="utf-8")
        exam.question_paper_url = str(question_paper)
        db.commit()

        context = service._load_exam_context(submission)
        assert context["evaluation_mode"] == "AI_AUTONOMOUS"
        assert context["total_marks"] == 50.0
        assert context["subject"] == "Biology"
        assert context["questions"]  # at least one parsed question


# ─────────────────────────────────────────────────────────────────────────
# delete_submission
# ─────────────────────────────────────────────────────────────────────────

class TestDeleteSubmission:
    def test_delete_nonexistent_returns_false(self, service):
        assert service.delete_submission(uuid4()) is False

    def test_delete_removes_files_from_disk(self, service, submission, tmp_path):
        sheet = tmp_path / "sheet.pdf"
        sheet.write_bytes(b"%PDF-1.4")
        submission.answer_sheet_path = str(sheet)
        service.db.commit()

        assert os.path.exists(sheet)
        result = service.delete_submission(submission.id)
        assert result is True
        assert not os.path.exists(sheet)
        assert service.get_submission(submission.id) is None

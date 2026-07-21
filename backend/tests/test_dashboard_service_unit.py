"""
Unit tests for DashboardService, calling it directly (bypassing the API
layer already covered by test_dashboard.py) to exercise branches the route
tests don't reach: zero-data edge cases, the exception fallback paths, and
_evaluation_mode_counts' fallback inference logic.
"""

from uuid import uuid4

import pytest

from app.core.database import Base
from app.models.exam import Exam, EvaluationMode
from app.models.submission import Submission, SubmissionStatus
from app.services.dashboard_service import DashboardService
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
    return DashboardService(db)


# ─────────────────────────────────────────────────────────────────────────
# get_overview_metrics — zero-data and division-by-zero guards
# ─────────────────────────────────────────────────────────────────────────

class TestOverviewMetricsEdgeCases:
    def test_teacher_with_no_exams_returns_zeroed_payload(self, service):
        """A brand-new teacher account must not error, and every rate/average
        must be a safe 0.0, not a division-by-zero exception."""
        result = service.get_overview_metrics(user_id=uuid4(), is_admin=False)

        assert result["total_exams"] == 0
        assert result["total_submissions"] == 0
        assert result["average_score"] == 0.0
        assert result["average_confidence"] == 0.0
        assert result["result_publication_rate"] == 0.0

    def test_exams_with_no_completed_submissions_returns_zero_averages(self, service, db):
        teacher_id = uuid4()
        exam = Exam(teacher_id=teacher_id, title="No Submissions Yet", subject="Math", total_marks=50)
        db.add(exam)
        db.commit()

        result = service.get_overview_metrics(user_id=teacher_id, is_admin=False)
        assert result["total_exams"] == 1
        assert result["total_submissions"] == 0
        assert result["average_score"] == 0.0
        assert result["published_exams_count"] == 0
        assert result["unpublished_exams_count"] == 1

    def test_admin_sees_all_teachers_exams(self, service, db):
        teacher_a, teacher_b = uuid4(), uuid4()
        db.add(Exam(teacher_id=teacher_a, title="A's Exam", subject="Physics", total_marks=50))
        db.add(Exam(teacher_id=teacher_b, title="B's Exam", subject="Chemistry", total_marks=50))
        db.commit()

        admin_result = service.get_overview_metrics(user_id=uuid4(), is_admin=True)
        assert admin_result["total_exams"] == 2

        teacher_result = service.get_overview_metrics(user_id=teacher_a, is_admin=False)
        assert teacher_result["total_exams"] == 1


class TestExamAnalyticsEdgeCases:
    def test_exam_with_no_submissions_returns_zeroed_scores(self, service, db):
        exam = Exam(teacher_id=uuid4(), title="Empty Exam", subject="History", total_marks=100)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        result = service.get_exam_analytics(exam.id)
        assert result["submission_count"] == 0
        assert result["average_score"] == 0.0
        assert result["completion_rate"] == 0.0

    def test_completed_submissions_without_marks_do_not_crash(self, service, db):
        """A COMPLETED submission with obtained_marks=None (edge case: evaluator
        set status but marks write failed) must be excluded from averaging,
        not crash the whole analytics call."""
        exam = Exam(teacher_id=uuid4(), title="Edge Case Exam", subject="Art", total_marks=100)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = Submission(
            exam_id=exam.id, student_name="No Marks", student_roll_number="X1",
            status=SubmissionStatus.COMPLETED, obtained_marks=None, total_marks=100.0,
        )
        db.add(sub)
        db.commit()

        result = service.get_exam_analytics(exam.id)
        assert result["submission_count"] == 1
        assert result["average_score"] == 0.0


class TestMonitoringDataEdgeCases:
    def test_no_exams_returns_empty_payload_shape(self, service):
        result = service.get_monitoring_data(user_id=uuid4(), is_admin=False)
        assert result["aggregate_analytics"]["total_submissions"] == 0
        assert result["fairness_metrics"]["bias_free_rate"] == 100.0
        assert set(result["score_distribution"].keys()) == {"90-100", "80-89", "70-79", "60-69", "below_60"}

    def test_submission_with_zero_total_marks_falls_into_below_60(self, service, db):
        """total_marks=0 must not raise ZeroDivisionError in score-bracket grouping."""
        teacher_id = uuid4()
        exam = Exam(teacher_id=teacher_id, title="Zero Marks Exam", subject="Music", total_marks=0)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = Submission(
            exam_id=exam.id, student_name="Zero Total", student_roll_number="Z1",
            status=SubmissionStatus.COMPLETED, obtained_marks=0.0, total_marks=0.0,
        )
        db.add(sub)
        db.commit()

        result = service.get_monitoring_data(user_id=teacher_id, is_admin=False)
        assert result["score_distribution"]["below_60"] == 1

    def test_failed_submissions_counted_separately_from_completed(self, service, db):
        teacher_id = uuid4()
        exam = Exam(teacher_id=teacher_id, title="Mixed Status Exam", subject="Geo", total_marks=50)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        db.add(Submission(
            exam_id=exam.id, student_name="Failed One", student_roll_number="F1",
            status=SubmissionStatus.FAILED,
        ))
        db.add(Submission(
            exam_id=exam.id, student_name="Completed One", student_roll_number="C1",
            status=SubmissionStatus.COMPLETED, obtained_marks=45.0, total_marks=50.0,
        ))
        db.commit()

        result = service.get_monitoring_data(user_id=teacher_id, is_admin=False)
        assert result["aggregate_analytics"]["failed_submissions"] == 1
        assert result["aggregate_analytics"]["completed_submissions"] == 1


class TestSubmissionReview:
    def test_nonexistent_submission_returns_none(self, service):
        assert service.get_submission_review(uuid4()) is None

    def test_submission_without_evaluation_output_returns_defaults_not_none(self, service, db):
        exam = Exam(teacher_id=uuid4(), title="Pending Exam", subject="CS", total_marks=100)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = Submission(
            exam_id=exam.id, student_name="Still Processing", student_roll_number="P1",
            status=SubmissionStatus.PROCESSING,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        result = service.get_submission_review(sub.id)
        assert result is not None
        assert result["question_breakdown"] == []
        assert result["feedback"]["summary"] == ""
        assert result["score"] == 0.0


class TestEvaluationModeCounts:
    def test_falls_back_to_exam_answer_key_presence_when_json_missing(self, service, db):
        """When the evaluation-output JSON can't be read, mode should be
        inferred from whether the exam has an answer key configured."""
        exam = Exam(
            teacher_id=uuid4(), title="Answer Key Exam", subject="Bio", total_marks=50,
            answer_key_url="some/path.txt", evaluation_mode=EvaluationMode.ANSWER_KEY,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = Submission(
            exam_id=exam.id, student_name="AK Student", student_roll_number="AK1",
            status=SubmissionStatus.COMPLETED, obtained_marks=40.0, total_marks=50.0,
            evaluation_output_path=None,  # forces fallback inference
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        counts = service._evaluation_mode_counts([sub])
        assert counts["ANSWER_KEY"] == 1
        assert counts["AI_AUTONOMOUS"] == 0

    def test_falls_back_to_autonomous_when_no_answer_key(self, service, db):
        exam = Exam(teacher_id=uuid4(), title="Autonomous Exam", subject="Bio", total_marks=50)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = Submission(
            exam_id=exam.id, student_name="Auto Student", student_roll_number="AU1",
            status=SubmissionStatus.COMPLETED, obtained_marks=30.0, total_marks=50.0,
            evaluation_output_path=None,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        counts = service._evaluation_mode_counts([sub])
        assert counts["AI_AUTONOMOUS"] == 1
        assert counts["ANSWER_KEY"] == 0

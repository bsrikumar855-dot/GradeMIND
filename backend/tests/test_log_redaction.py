"""A known PII string must never reach a log record.

Guards the log side of the anonymisation boundary (master spec §2.5). The
failure this prevents is not theoretical: dev-server logs on this project
reached 1.6 GB of request lines from a student-data pipeline, and the
application's own UPLOAD_STAGE lines logged roll numbers and answer-sheet
filenames as interpolated args.
"""

import logging

import pytest

from app.core.log_redaction import PIIRedactionFilter, redact

ROLL = "CS2024001"
NAME = "Jane Doe"


@pytest.fixture
def captured():
    """A logger with the redaction filter installed, capturing formatted output."""
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(self.format(record))

    handler = Capture()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(PIIRedactionFilter())

    logger = logging.getLogger("GradeMIND.test_redaction")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    yield logger, records

    logger.handlers = []


def test_roll_number_in_args_is_redacted(captured):
    """The real shape: PII passed as a %s arg, not baked into the format string."""
    logger, records = captured
    logger.info("UPLOAD_STAGE start exam_id=%s student_roll_number=%s", "abc", ROLL)

    assert ROLL not in records[0], records[0]
    assert "[REDACTED]" in records[0]


def test_student_name_is_redacted(captured):
    logger, records = captured
    logger.info("UPLOAD_STAGE student_name=%s status=ok", NAME)

    assert NAME not in records[0], records[0]


def test_storage_filename_is_redacted(captured):
    """Filenames are identifiers here: paths are {roll}_{uuid}.pdf."""
    logger, records = captured
    logger.info("UPLOAD_STAGE file_saved path=%s", "CS005_fe7deca0.pdf")

    assert "CS005" not in records[0], records[0]
    assert "fe7deca0" not in records[0], records[0]


def test_bearer_token_is_redacted(captured):
    logger, records = captured
    logger.info("auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in records[0]


def test_token_in_query_string_is_redacted(captured):
    logger, records = captured
    logger.info("GET /results?token=s3cr3tvalue&page=1 200")

    assert "s3cr3tvalue" not in records[0], records[0]
    assert "page=1" in records[0], "non-sensitive params must survive"


def test_ordinary_message_is_untouched(captured):
    logger, records = captured
    logger.info("Application startup complete")

    assert records[0] == "Application startup complete"


@pytest.mark.parametrize(
    "text",
    [
        f"student_roll_number={ROLL}",
        f"student_roll_number: {ROLL}",
        f"roll is {ROLL} today",
        "CS005_fe7deca0.pdf",
    ],
)
def test_redact_is_total_over_known_shapes(text):
    assert ROLL not in redact(text) or "CS005" in text
    assert "[REDACTED]" in redact(text)

"""A known PII string must never reach a log record.

Guards the log side of the anonymisation boundary (master spec §2.5). The
failure this prevents is not theoretical: dev-server logs on this project
reached 1.6 GB of request lines from a student-data pipeline, and the
application's own UPLOAD_STAGE lines logged roll numbers and answer-sheet
filenames as interpolated args.
"""

import logging
import secrets

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


JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJDUzIwMjQwMDEifQ.abc123signature"


@pytest.mark.parametrize(
    "label,message",
    [
        # The three live sites: results/page.tsx:201, reports/page.tsx:82,
        # feedback/page.tsx:149 all build `${API_URL}/submissions/${id}/pdf?token=${token}`.
        ("download url", f"GET /submissions/8f2a/pdf?token={JWT} 200 81ms"),
        # refresh_token was MISSED by the first version of the filter, which
        # matched token/key/api_key/access_token by name. This app issues
        # refresh tokens.
        ("refresh_token param", f"POST /auth/refresh?refresh_token={JWT}"),
        # A token does not stop being a credential because it is in a path
        # segment rather than a query string.
        ("path segment", f"GET /download/{JWT}/file.pdf"),
        ("bare in message", f"issuing token {JWT} for user"),
        ("authorization header", f"Authorization: Bearer {JWT}"),
        # The point of matching JWT shape rather than parameter name: a
        # parameter nobody anticipated still gets redacted.
        ("unanticipated param", f"GET /x?wibble={JWT}"),
    ],
)
def test_jwt_is_redacted_wherever_it_appears(captured, label, message):
    logger, records = captured
    logger.info("%s", message)

    assert JWT not in records[0], f"{label}: {records[0]}"
    assert "abc123signature" not in records[0], f"{label}: signature leaked"


def test_opaque_refresh_token_is_redacted(captured):
    """Format-independence: a non-JWT token must still be redacted.

    `create_refresh_token` issues a JWT today, so the `eyJ` anchor catches it.
    But `RefreshToken` stores a `token_hash`, so nothing structurally prevents
    a switch to opaque random tokens — and on that day an `eyJ`-anchored rule
    would silently stop matching and the filter would fail open.

    This test is the guard against that change landing unnoticed. It does not
    reference JWT structure at all.
    """
    logger, records = captured
    opaque = secrets.token_urlsafe(48)

    logger.info("POST /auth/refresh?refresh_token=%s", opaque)

    assert opaque not in records[0], records[0]


@pytest.mark.parametrize(
    "template",
    [
        "POST /auth/refresh?refresh_token={t}",
        "GET /download/{t}/file.pdf",
        "GET /x?parameter_nobody_anticipated={t}",
    ],
)
def test_opaque_secret_redacted_in_every_position(captured, template):
    logger, records = captured
    opaque = secrets.token_urlsafe(48)

    logger.info("%s", template.format(t=opaque))

    assert opaque not in records[0], records[0]


def test_bare_opaque_token_in_free_text_is_a_known_limitation(captured):
    """Documents a deliberate gap, so it is a decision rather than an oversight.

    The secret heuristic is scoped to query-parameter values and path segments.
    Extending it to bare whitespace-delimited text was tried and rejected: it
    redacts `sentence-transformers/all-MiniLM-L6-v2` (38 chars, mixed case,
    digits), which is the embedding model name Phase 2.6 requires on every
    evaluation record for reproducibility. Losing provenance to protect
    against a token that should not be logged bare in the first place is the
    wrong trade.

    A bare JWT is still caught by the structural rule. A bare *opaque* token
    is not. The defence there is not logging it — redaction is a backstop.
    """
    logger, records = captured
    opaque = secrets.token_urlsafe(48)

    logger.info("issuing %s to caller", opaque)

    assert opaque in records[0], (
        "Bare opaque tokens are now redacted — if that was intentional, "
        "check that model names and provenance strings still survive "
        "(test_provenance_strings_survive) and update this test."
    )


@pytest.mark.parametrize(
    "provenance",
    [
        "sentence-transformers/all-MiniLM-L6-v2",
        "BAAI/bge-large-en-v1.5",
        "GradeMIND-Backend-v1.0.0-rc2-build20260813",
    ],
)
def test_provenance_strings_survive(captured, provenance):
    """Model names and versions are required on every evaluation record.

    Phase 2.6 makes a stored result reproducible from its recorded versions.
    A redaction rule that eats the model name breaks that, silently.
    """
    logger, records = captured
    logger.info("evaluation model=%s", provenance)

    assert provenance in records[0], f"provenance redacted: {records[0]}"


def test_uuids_are_preserved(captured):
    """Deliberate non-redaction — this is a calibration decision, not a gap.

    Submission and exam ids are UUIDs and appear in nearly every log line.
    Redacting them would make logs useless for tracing a request, which is
    the thing logs exist for. A UUID is lowercase hex plus dashes; the
    secret heuristic requires mixed case and a digit, which separates the
    two without a tunable entropy threshold.
    """
    logger, records = captured
    submission_id = "3c1e31a4-1c73-48e0-9212-3028c5a3829b"

    logger.info("GET /submissions/%s/pdf 200", submission_id)

    assert submission_id in records[0], "traceability lost: UUID was redacted"


def test_hex_digest_is_preserved(captured):
    """Same reasoning: a sha is not a credential and is useful in logs."""
    logger, records = captured
    digest = "a3f5c9e1b7d2486fa3f5c9e1b7d2486fa3f5c9e1"

    logger.info("page_sha256=%s cached", digest)

    assert digest in records[0]


def test_non_credential_query_params_survive(captured):
    """Redaction must not eat ordinary telemetry."""
    logger, records = captured
    logger.info("GET /results?page=1&sort=name&exam_id=8f2a 200")

    assert "page=1" in records[0]
    assert "sort=name" in records[0]


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

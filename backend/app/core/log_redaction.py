"""PII redaction for application logs.

The same anonymisation boundary the evaluator sits behind (master spec §2.5),
applied to logs.

This is not hypothetical. `tmp/backend.err.log` on a dev machine reached
1.6 GB of uvicorn request lines from a pipeline that processes student answer
sheets, and the application's own `UPLOAD_STAGE` log lines carried
`student_roll_number` and answer-sheet filenames directly. Filenames here are
themselves identifiers — storage paths are built as
`{roll_number}_{uuid}.pdf`, so a filename in a log line is a roll number in a
log line.

A logging filter is a backstop, not a licence to log PII and rely on scrubbing.
The primary rule is still: do not put student identity into a log call.
"""

from __future__ import annotations

import logging
import re
from typing import List, Pattern, Tuple

REDACTED = "[REDACTED]"

# Ordered: more specific patterns first, so a roll number inside a filename is
# not partially rewritten by the bare-roll-number rule.
_PATTERNS: List[Tuple[Pattern[str], str]] = [
    # student_roll_number=CS2024001 / student_roll_number: CS2024001
    (
        re.compile(r"(student_roll_number\s*[=:]\s*)(\S+)", re.IGNORECASE),
        r"\1" + REDACTED,
    ),
    # student_name=Jane Doe — consumes to the next key=, comma, or end
    (
        re.compile(r"(student_name\s*[=:]\s*)([^,=]+?)(?=\s+\w+\s*[=:]|,|$)", re.IGNORECASE),
        r"\1" + REDACTED,
    ),
    # Storage filenames: {roll}_{hex}.{ext}
    (
        re.compile(r"\b[A-Za-z0-9]+_[0-9a-f]{6,}\.(pdf|png|jpe?g|json)\b", re.IGNORECASE),
        REDACTED + r".\1",
    ),
    # Bare roll numbers in the CS######## / 2-4 letters + 3-10 digits shape.
    (re.compile(r"\b[A-Z]{2,4}\d{3,10}\b"), REDACTED),
    # JWTs, matched STRUCTURALLY rather than by the parameter name carrying
    # them. A JWT is three base64url segments separated by dots, and the header
    # `{"` always base64url-encodes to a leading `eyJ`, which makes this
    # specific enough not to eat ordinary text.
    #
    # This is the primary token rule. Name-based rules below are a backstop,
    # and they are the wrong primary defence: the first version of this file
    # matched `?token=`, `?key=`, `?api_key=` and `?access_token=` — and missed
    # `?refresh_token=`, which this application actually issues. A token does
    # not stop being a credential because it arrived under a parameter name
    # nobody thought of, or in a path segment instead of a query string.
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}"),
        REDACTED,
    ),
    # Bearer tokens and API keys in URLs or headers.
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE), r"\1" + REDACTED),
    (
        re.compile(
            r"([?&](?:token|key|api_key|apikey|access_token|refresh_token|id_token"
            r"|auth|authorization|secret|password|signature|sig)=)[^&\s]+",
            re.IGNORECASE,
        ),
        r"\1" + REDACTED,
    ),
]


# ---------------------------------------------------------------------------
# Format-independent secret detection
# ---------------------------------------------------------------------------
#
# The JWT rule above is anchored on `eyJ`, which every JWT header produces.
# That is still a rule tied to the current implementation rather than to the
# property being defended — the same defect as matching parameter names.
# `create_refresh_token` happens to issue a JWT today, but `RefreshToken`
# stores a `token_hash`, so nothing structurally prevents a move to opaque
# random refresh tokens. The day that happens, `eyJ`-anchoring silently stops
# matching and the filter fails open.
#
# So: redact anything that *looks like a secret by construction* — long and
# high-entropy — wherever it appears in a query-parameter value or a path
# segment, regardless of format.
#
# Calibrated to exclude UUIDs deliberately. Submission and exam ids are UUIDs
# and appear in nearly every log line; redacting them would make logs useless
# for tracing a request. A UUID is lowercase hex plus dashes — 16 symbols, no
# uppercase. A base64url token draws on 64 symbols and mixes case. Requiring
# mixed case plus a digit separates them cleanly without needing a float
# entropy threshold that would need its own calibration.

# Scope: query-parameter values and path segments only, NOT bare text.
#
# Extending it to bare whitespace-delimited strings was tried and rejected.
# `sentence-transformers/all-MiniLM-L6-v2` is 38 characters with mixed case and
# digits, so it trips every secret test above — and it is the embedding model
# name that Phase 2.6 requires on every evaluation record for reproducibility.
# Redacting provenance to defend against a token that should not be logged bare
# in the first place is the wrong trade.
#
# Consequence, recorded rather than hidden: a bare *opaque* token in a log
# message is not redacted. A bare JWT still is, via the structural rule above.
# `backend/tests/test_log_redaction.py` pins both behaviours so the limit is a
# decision someone revisits, not a hole someone discovers.
MIN_SECRET_LENGTH = 32


def _looks_like_secret(value: str) -> bool:
    if len(value) < MIN_SECRET_LENGTH:
        return False
    if not any(c.isupper() for c in value):
        return False  # excludes lowercase-hex UUIDs and hex digests
    if not any(c.islower() for c in value):
        return False
    if not any(c.isdigit() for c in value):
        return False
    # Reject prose: a secret has no spaces, and few non-token characters.
    return all(c.isalnum() or c in "-_.=+/" for c in value)


_QUERY_VALUE = re.compile(r"([?&][A-Za-z0-9_.\-]+=)([^&\s]+)")
_PATH_SEGMENT = re.compile(r"(/)([^/\s?&#]+)")


def _redact_if_secret(match: "re.Match[str]") -> str:
    prefix, value = match.group(1), match.group(2)
    return prefix + REDACTED if _looks_like_secret(value) else match.group(0)


def redact(text: str) -> str:
    """Apply every redaction pattern to a string."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)

    # Format-independent pass, after the named rules so their more precise
    # replacements win where both apply.
    text = _QUERY_VALUE.sub(_redact_if_secret, text)
    text = _PATH_SEGMENT.sub(_redact_if_secret, text)
    return text


class PIIRedactionFilter(logging.Filter):
    """Logging filter that redacts PII from the formatted message and args.

    Attached to the root logger, so it covers application logs and uvicorn's
    access logs alike.

    Mutates ``record.msg`` and clears ``record.args`` after interpolation:
    redacting the format string alone would miss values supplied as args, which
    is exactly how the UPLOAD_STAGE lines were written
    (``logger.info("... roll=%s", roll)``).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            # A broken format string is the caller's bug, not ours, and must
            # not be silently swallowed into an unlogged event.
            return True

        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()

        return True


def install_pii_redaction() -> None:
    """Attach the filter to the root logger and to uvicorn's loggers.

    Filters on a logger do not apply to records from child loggers, so the
    filter is attached to handlers rather than relying on logger inheritance.
    """
    pii_filter = PIIRedactionFilter()

    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, PIIRedactionFilter) for f in handler.filters):
            handler.addFilter(pii_filter)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "GradeMIND"):
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            if not any(isinstance(f, PIIRedactionFilter) for f in handler.filters):
                handler.addFilter(pii_filter)
        if not any(isinstance(f, PIIRedactionFilter) for f in logger.filters):
            logger.addFilter(pii_filter)

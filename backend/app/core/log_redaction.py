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
    # Bearer tokens and API keys that end up in URLs or headers.
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE), r"\1" + REDACTED),
    (re.compile(r"([?&](?:token|key|api_key|access_token)=)[^&\s]+", re.IGNORECASE), r"\1" + REDACTED),
]


def redact(text: str) -> str:
    """Apply every redaction pattern to a string."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
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

"""Captured examiner corrections to transcription output.

Spec Amendment A section 2.7. Every correction an examiner makes to a line of
transcribed text is a labelled pair -- (what the model read, what it actually
says) -- on real handwriting, produced as a by-product of work someone was
doing anyway.

This is the path off assist-only. A labelled set is the one thing that unlocks
the AUTO lane, calibrates the semantic thresholds, and lets Phase 3 make an
accuracy claim at all. Collecting it costs nothing once examiners use the
system and is expensive to retrofit, because the corrections are only knowable
at the moment the examiner makes them: the original model output is gone once
the text is edited in place.

Data layer only. No UI, no API surface, no service wiring -- those come with
the examiner interface in Phase 5.

TWO PROPERTIES THIS TABLE MUST KEEP
-----------------------------------

1. APPEND-ONLY. A correction is an observation about what a human did at a
   moment in time. Editing one rewrites history and silently changes any
   metric computed from it. Rows are inserted and never updated or deleted;
   a mistaken correction is superseded by a later row, not overwritten.

2. NO IDENTITY. Evaluation runs on anonymised text (DPDP Act 2023, and the
   identity boundary in the master spec). These rows carry the extracted line
   text, so they inherit that boundary: they reference a submission by id and
   store no student name, roll number, or centre code. `original_text` and
   `corrected_text` hold transcribed answer content and must be written
   post-masking, never from a raw scan.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base, GUID


class TranscriptionCorrection(Base):
    """One examiner correction to one transcribed line.

    A row is a labelled pair for HTR training and evaluation:
    `original_text` is what the model produced, `corrected_text` is what the
    page actually says.
    """

    __tablename__ = "transcription_corrections"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)

    # What was being transcribed.
    submission_id = Column(
        GUID(), ForeignKey("submissions.id"), nullable=False, index=True
    )
    page_number = Column(Integer, nullable=False)
    line_index = Column(Integer, nullable=False)

    # The labelled pair. original_text is nullable because a correction may be
    # an INSERTION: the model produced no line at all where there is text on
    # the page. That is a different and more serious failure than misreading a
    # line, and collapsing the two by storing "" would hide it.
    original_text = Column(Text, nullable=True)
    corrected_text = Column(Text, nullable=False)

    # Provenance of the output being corrected. Without these a correction
    # cannot be attributed to the model version that produced it, so it cannot
    # be used to show that a change improved anything.
    provider = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    weights_sha256 = Column(String, nullable=True)
    preprocess_version = Column(String, nullable=True)

    # What the model thought at the time. The central question for the
    # confidence floor is whether low confidence actually predicts correction;
    # that cannot be asked later if the value is not recorded here.
    original_confidence = Column(Float, nullable=True)

    # Geometry, so a correction can be tied back to ink on the page.
    bbox_x0 = Column(Float, nullable=True)
    bbox_y0 = Column(Float, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)

    # Who and when. corrected_by is the examiner, a User -- not a student.
    corrected_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Set when the examiner accepts the model's line unchanged. Those rows are
    # NEGATIVE examples and are as necessary as the corrections: a set built
    # only from corrections is sampled entirely on model failure, and any error
    # rate computed from it is meaningless.
    is_confirmation = Column(Boolean, nullable=False, default=False, server_default="0")

    __table_args__ = (
        # The query that builds a training set: everything for a submission,
        # in page and line order.
        Index(
            "ix_transcription_corrections_submission_page_line",
            "submission_id",
            "page_number",
            "line_index",
        ),
        # Deliberately NOT unique. The same line may be corrected more than
        # once -- by a second examiner, or by the same one revising. Every
        # correction is kept; the latest by created_at wins for display, and
        # the disagreement between two examiners on one line is itself a
        # measurement of how legible that line is.
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        kind = "confirm" if self.is_confirmation else "correct"
        return (
            f"<TranscriptionCorrection {kind} submission={self.submission_id} "
            f"p{self.page_number}:l{self.line_index}>"
        )

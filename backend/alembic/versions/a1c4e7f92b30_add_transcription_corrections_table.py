"""add transcription_corrections table

Spec Amendment A section 2.7 -- capture every examiner correction to
transcription output as a labelled pair. Data layer only; no UI, no API.

Append-only by convention: rows are inserted and never updated or deleted. A
mistaken correction is superseded by a later row for the same line, not
overwritten, so the table stays a record of what humans actually did.

Revision ID: a1c4e7f92b30
Revises: 8f2d4c7a9b1e
Create Date: 2026-08-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.database import GUID

revision: str = "a1c4e7f92b30"
down_revision: Union[str, None] = "8f2d4c7a9b1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transcription_corrections",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("submission_id", GUID(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        # Nullable: a correction may be an INSERTION, where the model produced
        # no line at all. Storing "" would collapse that into a misread.
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("corrected_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("weights_sha256", sa.String(), nullable=True),
        sa.Column("preprocess_version", sa.String(), nullable=True),
        sa.Column("original_confidence", sa.Float(), nullable=True),
        sa.Column("bbox_x0", sa.Float(), nullable=True),
        sa.Column("bbox_y0", sa.Float(), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=True),
        sa.Column("bbox_y1", sa.Float(), nullable=True),
        sa.Column("corrected_by", GUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Confirmations are negative examples. A set built only from
        # corrections is sampled entirely on model failure.
        sa.Column(
            "is_confirmation",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["corrected_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transcription_corrections_id"),
        "transcription_corrections",
        ["id"],
    )
    op.create_index(
        op.f("ix_transcription_corrections_submission_id"),
        "transcription_corrections",
        ["submission_id"],
    )
    op.create_index(
        op.f("ix_transcription_corrections_corrected_by"),
        "transcription_corrections",
        ["corrected_by"],
    )
    op.create_index(
        op.f("ix_transcription_corrections_created_at"),
        "transcription_corrections",
        ["created_at"],
    )
    # The query that builds a training set.
    op.create_index(
        "ix_transcription_corrections_submission_page_line",
        "transcription_corrections",
        ["submission_id", "page_number", "line_index"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transcription_corrections_submission_page_line",
        table_name="transcription_corrections",
    )
    op.drop_index(
        op.f("ix_transcription_corrections_created_at"),
        table_name="transcription_corrections",
    )
    op.drop_index(
        op.f("ix_transcription_corrections_corrected_by"),
        table_name="transcription_corrections",
    )
    op.drop_index(
        op.f("ix_transcription_corrections_submission_id"),
        table_name="transcription_corrections",
    )
    op.drop_index(
        op.f("ix_transcription_corrections_id"),
        table_name="transcription_corrections",
    )
    op.drop_table("transcription_corrections")

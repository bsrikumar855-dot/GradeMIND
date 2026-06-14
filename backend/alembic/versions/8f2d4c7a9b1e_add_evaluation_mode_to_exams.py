"""add_evaluation_mode_to_exams

Revision ID: 8f2d4c7a9b1e
Revises: 5d9f3a1b7c8d
Create Date: 2026-06-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2d4c7a9b1e"
down_revision: Union[str, None] = "5d9f3a1b7c8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


evaluation_mode_enum = sa.Enum("ANSWER_KEY", "AI_AUTONOMOUS", name="evaluation_mode")


def upgrade() -> None:
    bind = op.get_bind()
    evaluation_mode_enum.create(bind, checkfirst=True)
    op.add_column(
        "exams",
        sa.Column(
            "evaluation_mode",
            evaluation_mode_enum,
            nullable=False,
            server_default="AI_AUTONOMOUS",
        ),
    )
    op.execute(
        "UPDATE exams SET evaluation_mode = 'ANSWER_KEY' "
        "WHERE answer_key_url IS NOT NULL AND answer_key_url <> ''"
    )


def downgrade() -> None:
    op.drop_column("exams", "evaluation_mode")
    bind = op.get_bind()
    evaluation_mode_enum.drop(bind, checkfirst=True)

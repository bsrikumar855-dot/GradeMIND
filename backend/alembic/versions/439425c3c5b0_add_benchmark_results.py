"""add_benchmark_results

Revision ID: 439425c3c5b0
Revises: 8f2d4c7a9b1e
Create Date: 2026-08-18 18:14:21.504970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '439425c3c5b0'
down_revision: Union[str, None] = '8f2d4c7a9b1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'benchmark_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False),
        sa.Column('marks', sa.Float(), nullable=False),
        sa.Column('student_answer', sa.Text(), nullable=True),
        sa.Column('human_score', sa.Float(), nullable=False),
        sa.Column('ai_score', sa.Float(), nullable=False),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('evaluation_mode', sa.String(length=50), nullable=False),
        sa.Column('ocr_quality', sa.String(length=50), nullable=True),
        sa.Column('review_required', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_results_id'), 'benchmark_results', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_results_subject'), 'benchmark_results', ['subject'], unique=False)
    op.create_index(op.f('ix_benchmark_results_question_type'), 'benchmark_results', ['question_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_benchmark_results_question_type'), table_name='benchmark_results')
    op.drop_index(op.f('ix_benchmark_results_subject'), table_name='benchmark_results')
    op.drop_index(op.f('ix_benchmark_results_id'), table_name='benchmark_results')
    op.drop_table('benchmark_results')

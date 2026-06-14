"""add_results_published_to_exams

Revision ID: 5d9f3a1b7c8d
Revises: 4f8a2e3d1b7c
Create Date: 2026-06-13 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d9f3a1b7c8d'
down_revision: Union[str, None] = '4f8a2e3d1b7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns results_published and published_at to exams table
    op.add_column('exams', sa.Column('results_published', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('exams', sa.Column('published_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('exams', 'published_at')
    op.drop_column('exams', 'results_published')

"""refactor subject and add examination

Revision ID: a362a311295d
Revises: 50203e116dcf
Create Date: 2026-04-09 13:38:44.664679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a362a311295d'
down_revision: Union[str, Sequence[str], None] = '50203e116dcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create examinations table
    op.create_table('examinations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch', sa.String(), nullable=True),
        sa.Column('branch_code', sa.String(), nullable=True),
        sa.Column('exam_code', sa.String(), nullable=True),
        sa.Column('exam_title', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('subject_code', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_examinations_exam_code'), 'examinations', ['exam_code'], unique=True)
    op.create_index(op.f('ix_examinations_id'), 'examinations', ['id'], unique=False)

    # 2. Update subjects table
    # Rename code to subject_code
    op.alter_column('subjects', 'code', new_column_name='subject_code')
    op.create_index(op.f('ix_subjects_subject_code'), 'subjects', ['subject_code'], unique=True)
    
    # Rename exam_year to year
    op.alter_column('subjects', 'exam_year', new_column_name='year')
    
    # Drop exam_title
    op.drop_column('subjects', 'exam_title')

    # 3. Update questions table
    op.add_column('questions', sa.Column('exam_code', sa.String(), nullable=True))
    op.create_index(op.f('ix_questions_exam_code'), 'questions', ['exam_code'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 3. Revoke questions changes
    op.drop_index(op.f('ix_questions_exam_code'), table_name='questions')
    op.drop_column('questions', 'exam_code')

    # 2. Revoke subjects changes
    op.add_column('subjects', sa.Column('exam_title', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.alter_column('subjects', 'year', new_column_name='exam_year')
    op.drop_index(op.f('ix_subjects_subject_code'), table_name='subjects')
    op.alter_column('subjects', 'subject_code', new_column_name='code')
    op.create_index('ix_subjects_code', 'subjects', ['code'], unique=False)

    # 1. Drop examinations table
    op.drop_index(op.f('ix_examinations_id'), table_name='examinations')
    op.drop_index(op.f('ix_examinations_exam_code'), table_name='examinations')
    op.drop_table('examinations')

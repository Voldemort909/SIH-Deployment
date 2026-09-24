"""add_missing_schema_columns

Revision ID: e1b2c3d4e5f6
Revises: c0b1dec9a095
Create Date: 2026-09-25 02:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1b2c3d4e5f6'
down_revision = 'c0b1dec9a095'
branch_labels = None
depends_on = None


def upgrade():
    # 1. companies
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('domains', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('recruitment_process', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('videos_json', sa.Text(), nullable=True))

    # 2. jobs
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('domain', sa.String(length=100), server_default='Software Engineering', nullable=False))
        batch_op.add_column(sa.Column('ctc', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('eligible_batch_years', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))

    # 3. job_skills
    with op.batch_alter_table('job_skills', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority', sa.String(length=50), server_default='Important', nullable=False))

    # 4. assessments
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('job_id', sa.Integer(), nullable=True))

    # 5. assessment_attempts
    with op.batch_alter_table('assessment_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('answers_json', sa.Text(), nullable=True))

    # 6. feedback
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('technical_rating', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('problem_solving_rating', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('communication_rating', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recommendation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('is_visible_to_student', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_column('is_visible_to_student')
        batch_op.drop_column('recommendation')
        batch_op.drop_column('communication_rating')
        batch_op.drop_column('problem_solving_rating')
        batch_op.drop_column('technical_rating')

    with op.batch_alter_table('assessment_attempts', schema=None) as batch_op:
        batch_op.drop_column('answers_json')

    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_column('job_id')

    with op.batch_alter_table('job_skills', schema=None) as batch_op:
        batch_op.drop_column('priority')

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('eligible_batch_years')
        batch_op.drop_column('ctc')
        batch_op.drop_column('domain')

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_column('videos_json')
        batch_op.drop_column('recruitment_process')
        batch_op.drop_column('domains')

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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    def col_exists(table, column):
        if table not in existing_tables:
            return False
        cols = {c['name'].lower() for c in inspector.get_columns(table)}
        return column.lower() in cols

    # 1. students
    if 'students' in existing_tables:
        with op.batch_alter_table('students', schema=None) as batch_op:
            if not col_exists('students', 'backlogs'):
                batch_op.add_column(sa.Column('backlogs', sa.Integer(), server_default='0', nullable=False))
            if not col_exists('students', 'certifications'):
                batch_op.add_column(sa.Column('certifications', sa.Text(), nullable=True))
            if not col_exists('students', 'experience'):
                batch_op.add_column(sa.Column('experience', sa.Text(), nullable=True))

    # 2. alumni
    if 'alumni' in existing_tables:
        with op.batch_alter_table('alumni', schema=None) as batch_op:
            if not col_exists('alumni', 'phone'):
                batch_op.add_column(sa.Column('phone', sa.String(length=50), nullable=True))
            if not col_exists('alumni', 'is_verified'):
                batch_op.add_column(sa.Column('is_verified', sa.Boolean(), server_default='1', nullable=False))
            if not col_exists('alumni', 'consent_share_contact'):
                batch_op.add_column(sa.Column('consent_share_contact', sa.Boolean(), server_default='0', nullable=False))

    # 3. placement_drives
    if 'placement_drives' in existing_tables:
        with op.batch_alter_table('placement_drives', schema=None) as batch_op:
            if not col_exists('placement_drives', 'max_backlogs'):
                batch_op.add_column(sa.Column('max_backlogs', sa.Integer(), server_default='0', nullable=False))
            if not col_exists('placement_drives', 'job_role'):
                batch_op.add_column(sa.Column('job_role', sa.String(length=150), nullable=True))
            if not col_exists('placement_drives', 'package_ctc'):
                batch_op.add_column(sa.Column('package_ctc', sa.String(length=100), nullable=True))
            if not col_exists('placement_drives', 'required_skills'):
                batch_op.add_column(sa.Column('required_skills', sa.Text(), nullable=True))
            if not col_exists('placement_drives', 'current_stage'):
                batch_op.add_column(sa.Column('current_stage', sa.String(length=50), server_default='Registration', nullable=False))

    # 4. placement_drive_students
    if 'placement_drive_students' in existing_tables:
        with op.batch_alter_table('placement_drive_students', schema=None) as batch_op:
            if not col_exists('placement_drive_students', 'stage'):
                batch_op.add_column(sa.Column('stage', sa.String(length=50), server_default='Registration', nullable=False))
            if not col_exists('placement_drive_students', 'offered_ctc'):
                batch_op.add_column(sa.Column('offered_ctc', sa.Numeric(precision=12, scale=2), nullable=True))
            if not col_exists('placement_drive_students', 'notes'):
                batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))

    # 5. student_preferences
    if 'student_preferences' in existing_tables:
        with op.batch_alter_table('student_preferences', schema=None) as batch_op:
            if not col_exists('student_preferences', 'preferred_domain'):
                batch_op.add_column(sa.Column('preferred_domain', sa.String(length=150), nullable=True))
            if not col_exists('student_preferences', 'job_type_preference'):
                batch_op.add_column(sa.Column('job_type_preference', sa.String(length=50), server_default='Both', nullable=False))

    # 6. notifications
    if 'notifications' in existing_tables:
        with op.batch_alter_table('notifications', schema=None) as batch_op:
            if not col_exists('notifications', 'channel'):
                batch_op.add_column(sa.Column('channel', sa.String(length=50), server_default='in_app', nullable=False))

    # 7. companies
    if 'companies' in existing_tables:
        with op.batch_alter_table('companies', schema=None) as batch_op:
            if not col_exists('companies', 'domains'):
                batch_op.add_column(sa.Column('domains', sa.String(length=255), nullable=True))
            if not col_exists('companies', 'recruitment_process'):
                batch_op.add_column(sa.Column('recruitment_process', sa.Text(), nullable=True))
            if not col_exists('companies', 'videos_json'):
                batch_op.add_column(sa.Column('videos_json', sa.Text(), nullable=True))

    # 8. jobs
    if 'jobs' in existing_tables:
        with op.batch_alter_table('jobs', schema=None) as batch_op:
            if not col_exists('jobs', 'domain'):
                batch_op.add_column(sa.Column('domain', sa.String(length=100), server_default='Software Engineering', nullable=False))
            if not col_exists('jobs', 'ctc'):
                batch_op.add_column(sa.Column('ctc', sa.String(length=100), nullable=True))
            if not col_exists('jobs', 'eligible_batch_years'):
                batch_op.add_column(sa.Column('eligible_batch_years', sa.String(length=100), nullable=True))
            if not col_exists('jobs', 'rejection_reason'):
                batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))

    # 9. job_skills
    if 'job_skills' in existing_tables:
        with op.batch_alter_table('job_skills', schema=None) as batch_op:
            if not col_exists('job_skills', 'priority'):
                batch_op.add_column(sa.Column('priority', sa.String(length=50), server_default='Important', nullable=False))

    # 10. assessments
    if 'assessments' in existing_tables:
        with op.batch_alter_table('assessments', schema=None) as batch_op:
            if not col_exists('assessments', 'job_id'):
                batch_op.add_column(sa.Column('job_id', sa.Integer(), nullable=True))

    # 11. assessment_attempts
    if 'assessment_attempts' in existing_tables:
        with op.batch_alter_table('assessment_attempts', schema=None) as batch_op:
            if not col_exists('assessment_attempts', 'answers_json'):
                batch_op.add_column(sa.Column('answers_json', sa.Text(), nullable=True))

    # 12. feedback
    if 'feedback' in existing_tables:
        with op.batch_alter_table('feedback', schema=None) as batch_op:
            if not col_exists('feedback', 'technical_rating'):
                batch_op.add_column(sa.Column('technical_rating', sa.Integer(), nullable=True))
            if not col_exists('feedback', 'problem_solving_rating'):
                batch_op.add_column(sa.Column('problem_solving_rating', sa.Integer(), nullable=True))
            if not col_exists('feedback', 'communication_rating'):
                batch_op.add_column(sa.Column('communication_rating', sa.Integer(), nullable=True))
            if not col_exists('feedback', 'recommendation'):
                batch_op.add_column(sa.Column('recommendation', sa.String(length=50), nullable=True))
            if not col_exists('feedback', 'is_visible_to_student'):
                batch_op.add_column(sa.Column('is_visible_to_student', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    pass

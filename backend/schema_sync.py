"""
Database Schema Synchronizer
Ensures all tables and newly added model columns exist across MySQL, PostgreSQL, and SQLite.
"""
from sqlalchemy import inspect, text
from backend.extensions import db


def sync_missing_columns():
    """
    Inspects existing database tables and dynamically adds any missing columns
    that were introduced to the SQLAlchemy models after initial migrations.
    Safe and idempotent on all supported SQL dialects.
    """
    try:
        # 0. Ensure all models are registered in metadata
        import backend.models  # noqa: F401

        # 1. First ensure all base tables exist
        db.create_all()

        # 2. Inspect existing schema
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        # Table -> list of (column_name, column_type_definition)
        columns_to_ensure = {
            "students": [
                ("backlogs", "INTEGER DEFAULT 0"),
                ("certifications", "TEXT"),
                ("experience", "TEXT")
            ],
            "alumni": [
                ("phone", "VARCHAR(50)"),
                ("is_verified", "BOOLEAN DEFAULT 1"),
                ("consent_share_contact", "BOOLEAN DEFAULT 0")
            ],
            "placement_drives": [
                ("max_backlogs", "INTEGER DEFAULT 0"),
                ("job_role", "VARCHAR(150)"),
                ("package_ctc", "VARCHAR(100)"),
                ("required_skills", "TEXT"),
                ("current_stage", "VARCHAR(50) DEFAULT 'Registration'")
            ],
            "placement_drive_students": [
                ("stage", "VARCHAR(50) DEFAULT 'Registration'"),
                ("offered_ctc", "NUMERIC(12, 2)"),
                ("notes", "TEXT")
            ],
            "student_preferences": [
                ("preferred_domain", "VARCHAR(150)"),
                ("job_type_preference", "VARCHAR(50) DEFAULT 'Both'")
            ],
            "notifications": [
                ("channel", "VARCHAR(50) DEFAULT 'in_app'")
            ],
            "companies": [
                ("domains", "VARCHAR(255)"),
                ("recruitment_process", "TEXT"),
                ("videos_json", "TEXT")
            ],
            "jobs": [
                ("domain", "VARCHAR(100) DEFAULT 'Software Engineering'"),
                ("ctc", "VARCHAR(100)"),
                ("eligible_batch_years", "VARCHAR(100)"),
                ("rejection_reason", "TEXT")
            ],
            "job_skills": [
                ("priority", "VARCHAR(50) DEFAULT 'Important'")
            ],
            "assessments": [
                ("job_id", "INTEGER")
            ],
            "assessment_attempts": [
                ("answers_json", "TEXT")
            ],
            "feedback": [
                ("technical_rating", "INTEGER"),
                ("problem_solving_rating", "INTEGER"),
                ("communication_rating", "INTEGER"),
                ("recommendation", "VARCHAR(50)"),
                ("is_visible_to_student", "BOOLEAN DEFAULT 0")
            ],
            "industry_experts": [
                ("status", "VARCHAR(50) DEFAULT 'PENDING'")
            ]
        }

        for table, columns in columns_to_ensure.items():
            if table in existing_tables:
                col_info = inspector.get_columns(table)
                existing_cols = {c["name"].lower() for c in col_info}
                for col_name, col_def in columns:
                    if col_name.lower() not in existing_cols:
                        try:
                            with db.engine.begin() as conn:
                                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                            print(f" [SCHEMA] Added column '{col_name}' to table '{table}'")
                        except Exception as err:
                            print(f" [SCHEMA] Note adding '{col_name}' to '{table}': {err}")
    except Exception as e:
        print(f" [SCHEMA] Warning during schema synchronization: {e}")

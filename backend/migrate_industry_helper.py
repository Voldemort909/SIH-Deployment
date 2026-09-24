import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from sqlalchemy import text

def sync_industry_schema():
    app = create_app()
    with app.app_context():
        # Ensure all tables exist first
        db.create_all()

        # 1. Update companies table
        c_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(companies)")).fetchall()]
        print("Existing companies columns:", c_cols)
        new_comp_cols = [
            ("domains", "VARCHAR(255)"),
            ("recruitment_process", "TEXT"),
            ("videos_json", "TEXT")
        ]
        for col_name, col_type in new_comp_cols:
            if col_name not in c_cols:
                db.session.execute(text(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}"))
                print(f"Added column companies.{col_name}")

        # 2. Update assessments table
        a_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(assessments)")).fetchall()]
        print("Existing assessments columns:", a_cols)
        if "job_id" not in a_cols:
            db.session.execute(text("ALTER TABLE assessments ADD COLUMN job_id INTEGER"))
            print("Added column assessments.job_id")

        # 3. Update assessment_attempts table
        att_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(assessment_attempts)")).fetchall()]
        print("Existing assessment_attempts columns:", att_cols)
        if "answers_json" not in att_cols:
            db.session.execute(text("ALTER TABLE assessment_attempts ADD COLUMN answers_json TEXT"))
            print("Added column assessment_attempts.answers_json")

        # 4. Update feedback table
        f_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(feedback)")).fetchall()]
        print("Existing feedback columns:", f_cols)
        new_feedback_cols = [
            ("technical_rating", "INTEGER"),
            ("problem_solving_rating", "INTEGER"),
            ("communication_rating", "INTEGER"),
            ("recommendation", "VARCHAR(50)"),
            ("is_visible_to_student", "BOOLEAN DEFAULT 0")
        ]
        for col_name, col_type in new_feedback_cols:
            if col_name not in f_cols:
                db.session.execute(text(f"ALTER TABLE feedback ADD COLUMN {col_name} {col_type}"))
                print(f"Added column feedback.{col_name}")

        db.session.commit()
        print("Industry schema migration completed successfully!")

if __name__ == "__main__":
    sync_industry_schema()

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from sqlalchemy import text

def sync_schema():
    app = create_app()
    with app.app_context():
        # 1. Update jobs table
        cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(jobs)")).fetchall()]
        print("Existing jobs columns:", cols)
        
        new_job_cols = [
            ("ctc", "VARCHAR(100)"),
            ("domain", "VARCHAR(100) DEFAULT 'Software Engineering'"),
            ("eligible_batch_years", "VARCHAR(100)"),
            ("rejection_reason", "TEXT")
        ]
        for col_name, col_type in new_job_cols:
            if col_name not in cols:
                db.session.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}"))
                print(f"Added column jobs.{col_name}")

        # 2. Update job_skills table
        js_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(job_skills)")).fetchall()]
        print("Existing job_skills columns:", js_cols)
        if "priority" not in js_cols:
            db.session.execute(text("ALTER TABLE job_skills ADD COLUMN priority VARCHAR(50) DEFAULT 'Important'"))
            print("Added column job_skills.priority")

        db.session.commit()
        print("Database schema migration successful!")

if __name__ == "__main__":
    sync_schema()

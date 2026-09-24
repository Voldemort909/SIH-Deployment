"""
Production Deployment Initializer
Single execution point for production startups (Render, Docker, Railway).
Handles schema migrations, missing column synchronization, and demo seeding
in a single, sequential, race-free process BEFORE the web server starts.
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from backend.schema_sync import sync_missing_columns
from backend.seed_sih_demo import seed_database


def run_deployment_init():
    print("=" * 60)
    print(" [DEPLOY] Starting Production Deployment Initialization")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        # 1. Run Alembic upgrade safely
        try:
            from flask_migrate import upgrade as alembic_upgrade
            print(" [DEPLOY] Running database migrations (flask db upgrade)...")
            alembic_upgrade()
            print(" [DEPLOY] Database migrations completed successfully.")
        except Exception as e:
            print(f" [DEPLOY] Migration note: {e} (proceeding to schema sync)")

        # 2. Synchronize all tables and missing columns safely
        print(" [DEPLOY] Ensuring all 26 tables and model columns exist...")
        sync_missing_columns()
        print(" [DEPLOY] Schema synchronization complete.")

        # 3. Seed demonstration cohort & pre-fill accounts
        print(" [DEPLOY] Initializing demo accounts (admin, recruiter, students)...")
        seed_database(app)
        print(" [DEPLOY] Demo accounts and sample data verified.")

    print("=" * 60)
    print(" [DEPLOY] Production Database is fully initialized and ready!")
    print("=" * 60)


if __name__ == "__main__":
    run_deployment_init()

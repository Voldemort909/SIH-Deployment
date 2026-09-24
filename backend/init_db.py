"""
Database Initialization and Seeding Script.
Creates all database tables, seeds baseline skills, and provisions a default Administrator account.

Usage:
    python backend/init_db.py
"""
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from backend.models import Skill, User, Admin


DEFAULT_SKILLS = [
    # Programming & Frameworks
    ("Python", "Programming"),
    ("Java", "Programming"),
    ("C++", "Programming"),
    ("JavaScript", "Programming"),
    ("TypeScript", "Programming"),
    ("Flask", "Backend Framework"),
    ("Django", "Backend Framework"),
    ("FastAPI", "Backend Framework"),
    ("React", "Frontend Framework"),
    ("Node.js", "Backend Runtime"),
    # Databases & Cloud
    ("MySQL", "Database"),
    ("PostgreSQL", "Database"),
    ("MongoDB", "Database"),
    ("Docker", "DevOps / Cloud"),
    ("AWS", "DevOps / Cloud"),
    ("Git", "Tools"),
    # Core CS & Soft Skills
    ("Data Structures & Algorithms", "Core CS"),
    ("Object-Oriented Programming", "Core CS"),
    ("Database Management Systems", "Core CS"),
    ("Operating Systems", "Core CS"),
    ("Problem Solving", "Soft Skill"),
    ("Communication", "Soft Skill"),
    ("Teamwork", "Soft Skill"),
]


def init_database():
    app = create_app()
    with app.app_context():
        print(f"Connecting to database: {app.config['SQLALCHEMY_DATABASE_URI']}...")
        db.create_all()
        print("Successfully ensured all 26 database tables!")

        # 1. Seed initial skills if table is empty
        if Skill.query.count() == 0:
            print("Seeding default skill catalog...")
            for name, category in DEFAULT_SKILLS:
                skill = Skill(name=name, category=category)
                db.session.add(skill)
            db.session.commit()
            print(f"Successfully seeded {len(DEFAULT_SKILLS)} foundational skills.")
        else:
            print(f"Skills catalog already contains {Skill.query.count()} skills.")

        # 2. Seed default Admin account if no admin exists
        admin_user = User.query.filter_by(role="admin").first()
        if not admin_user:
            print("Creating default Administrator account (admin@college.edu)...")
            admin_user = User(
                email="admin@college.edu",
                role="admin",
                is_active=True,
                is_verified=True
            )
            admin_default_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "AdminDefault#2026")
            admin_user.set_password(admin_default_pass)
            db.session.add(admin_user)
            db.session.flush()

            admin_profile = Admin(
                user_id=admin_user.id,
                first_name="Institutional",
                last_name="Placement Admin",
                staff_id="TPO-ADMIN-01",
                designation="Head Placement Officer",
                department="Training & Placement Cell"
            )
            db.session.add(admin_profile)
            db.session.commit()
            print("Default administrator created successfully. (Email: admin@college.edu, password configured via ADMIN_DEFAULT_PASSWORD)")
        else:
            print(f"Administrator account already exists: {admin_user.email}")


if __name__ == "__main__":
    init_database()

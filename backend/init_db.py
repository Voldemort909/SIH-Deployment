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
        from backend.schema_sync import sync_missing_columns
        sync_missing_columns()
        print("Successfully ensured all 26 database tables and synchronized schema columns!")

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
            admin_default_pass = os.getenv("ADMIN_DEFAULT_PASSWORD") or os.getenv("DEMO_ADMIN_PASSWORD") or os.getenv("DEMO_USER_PASSWORD") or "Admin@12345"
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
            print("Default administrator created successfully. (Email: admin@college.edu)")
        else:
            print(f"Administrator account already exists: {admin_user.email}")

        # 3. Seed default Recruiter account if missing
        recruiter_user = User.query.filter_by(email="recruiter@company.com").first()
        if not recruiter_user:
            print("Creating default Recruiter account (recruiter@company.com)...")
            from backend.models.company import Company
            from backend.models.user import IndustryExpert
            comp = Company.query.first()
            if not comp:
                comp = Company(name="TechCorp Solutions", industry_type="Software & Cloud")
                db.session.add(comp)
                db.session.flush()

            recruiter_user = User(
                email="recruiter@company.com",
                role="industry_expert",
                is_active=True,
                is_verified=True
            )
            rec_pass = os.getenv("DEMO_RECRUITER_PASSWORD") or os.getenv("DEMO_USER_PASSWORD") or "Recruiter@123"
            recruiter_user.set_password(rec_pass)
            db.session.add(recruiter_user)
            db.session.flush()

            expert = IndustryExpert(
                user_id=recruiter_user.id,
                company_id=comp.id,
                first_name="Siddharth",
                last_name="Nair",
                designation="Talent Acquisition Lead",
                experience_years=8,
                status="APPROVED"
            )
            db.session.add(expert)
            db.session.commit()
            print("Default recruiter created successfully. (Email: recruiter@company.com)")

        # 4. Seed default Student account if missing
        student_user = User.query.filter_by(email="rahul@college.edu").first()
        if not student_user:
            print("Creating default Student account (rahul@college.edu)...")
            from backend.models.user import Student
            student_user = User(
                email="rahul@college.edu",
                role="student",
                is_active=True,
                is_verified=True
            )
            stu_pass = os.getenv("DEMO_STUDENT_PASSWORD") or os.getenv("DEMO_USER_PASSWORD") or "Student@123"
            student_user.set_password(stu_pass)
            db.session.add(student_user)
            db.session.flush()

            student = Student(
                user_id=student_user.id,
                roll_number="CS2025-001",
                first_name="Rahul",
                last_name="Gupta",
                department="Computer Science",
                degree="B.Tech Computer Science",
                batch_year=2025,
                cgpa=7.50,
                backlogs=0
            )
            db.session.add(student)
            db.session.commit()
            print("Default student created successfully. (Email: rahul@college.edu)")


if __name__ == "__main__":
    init_database()

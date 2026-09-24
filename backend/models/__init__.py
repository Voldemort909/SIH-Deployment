"""
Database Models Package.
Exports all 26 normalized SQLAlchemy models for the College Placement & Career Development Platform.
Ensures Flask-Migrate and SQLAlchemy metadata discover every entity.
"""
from backend.models.base import TimestampMixin
from backend.models.user import User, Student, IndustryExpert, Admin
from backend.models.student import StudentPreference, Project
from backend.models.company import Company, CompanyHiringHistory
from backend.models.skill import Skill, StudentSkill, JobSkill
from backend.models.job import Job
from backend.models.resume import Resume, ResumeAnalysis
from backend.models.application import Application, ApplicationStatusHistory, Feedback
from backend.models.placement import PlacementRecord, PlacementDrive, PlacementDriveStudent, Alumni, Announcement, StudentIntervention
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.assessment import Assessment, AssessmentQuestion, AssessmentAttempt
from backend.models.notification import Notification

__all__ = [
    "TimestampMixin",
    # Roles & Users
    "User",
    "Student",
    "IndustryExpert",
    "Admin",
    # Profiles & Skills
    "StudentPreference",
    "Project",
    "Skill",
    "StudentSkill",
    # Corporate & Jobs
    "Company",
    "CompanyHiringHistory",
    "Job",
    "JobSkill",
    # Resumes
    "Resume",
    "ResumeAnalysis",
    # Applications & Feedback
    "Application",
    "ApplicationStatusHistory",
    "Feedback",
    # Placements & Alumni
    "PlacementRecord",
    "PlacementDrive",
    "PlacementDriveStudent",
    "Alumni",
    "Announcement",
    "StudentIntervention",
    # Workshops
    "Workshop",
    "WorkshopRegistration",
    # Assessments
    "Assessment",
    "AssessmentQuestion",
    "AssessmentAttempt",
    # Notifications
    "Notification",
]

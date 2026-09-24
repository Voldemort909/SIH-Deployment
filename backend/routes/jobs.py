"""
Job Discovery and Application Routes for Students.
Provides marketplace search, multi-faceted filtering, explainable matching,
and job application submission.
"""
from datetime import datetime, timezone
from flask import Blueprint, request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.job import Job
from backend.models.company import Company
from backend.models.skill import Skill, JobSkill
from backend.models.application import Application, ApplicationStatusHistory
from backend.models.user import User, Student
from backend.services.job_matcher import calculate_job_match
from backend.utils.auth import student_required, decode_token
from backend.utils.response import api_response, error_response

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


def get_current_student_optional():
    """Extracts student profile from token if present, without enforcing authentication."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        return None
    user = User.query.get(payload.get("sub"))
    if user and user.role == "student" and user.student_profile:
        return user.student_profile
    return None


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    """
    Lists published job openings with filtering and explainable matching.
    Filters:
      - domain (e.g. 'Software Engineering', 'AI/ML')
      - role (e.g. 'Software Engineer', 'Frontend')
      - company (Company name)
      - location (City / Remote / Hybrid)
      - job_type ('Full-time', 'Internship')
      - skill (Filter by required skill name)
      - search (Search across title, description, company)
      - eligible_only ('true' to filter only eligible jobs for authenticated student)
    """
    student = get_current_student_optional()

    query = Job.query.filter_by(status="Published")

    # 1. Apply Search query
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.join(Company, isouter=True).filter(
            or_(
                Job.title.ilike(search_pattern),
                Job.description.ilike(search_pattern),
                Job.domain.ilike(search_pattern),
                Job.location.ilike(search_pattern),
                Company.name.ilike(search_pattern)
            )
        )

    # 2. Domain Filter
    domain = request.args.get("domain", "").strip()
    if domain:
        query = query.filter(Job.domain.ilike(f"%{domain}%"))

    # 3. Role / Title Filter
    role = request.args.get("role", "").strip()
    if role:
        query = query.filter(Job.title.ilike(f"%{role}%"))

    # 4. Company Filter
    company_name = request.args.get("company", "").strip()
    if company_name:
        query = query.join(Company, isouter=True).filter(Company.name.ilike(f"%{company_name}%"))

    # 5. Location Filter
    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    # 6. Job Type Filter
    job_type = request.args.get("job_type", "").strip()
    if job_type:
        query = query.filter(Job.job_type.ilike(f"%{job_type}%"))

    # 7. Skill Filter
    skill_filter = request.args.get("skill", "").strip()
    if skill_filter:
        query = query.join(JobSkill).join(Skill).filter(Skill.name.ilike(f"%{skill_filter}%"))

    jobs = query.order_by(Job.created_at.desc()).all()

    # Pre-fetch student's applied job IDs if student is logged in
    applied_job_ids = set()
    if student:
        applied_job_ids = set(a.job_id for a in student.applications)

    results = []
    for j in jobs:
        # Collect prioritized skills
        skills_summary = {
            "critical": [js.skill.name for js in j.required_skills if js.skill and (js.priority or "").capitalize() == "Critical"],
            "important": [js.skill.name for js in j.required_skills if js.skill and (js.priority or "").capitalize() == "Important"],
            "preferred": [js.skill.name for js in j.required_skills if js.skill and (js.priority or "").capitalize() == "Preferred"]
        }

        # Calculate Explainable Match Score if student is logged in
        match_info = None
        if student:
            match_info = calculate_job_match(student, j)

        # Filter out ineligible if requested
        if request.args.get("eligible_only", "").lower() in ["true", "1"] and match_info and not match_info["eligibility"]["is_eligible"]:
            continue

        item = {
            "id": j.id,
            "title": j.title,
            "company": {
                "id": j.company.id if j.company else None,
                "name": j.company.name if j.company else "Top Recruiter",
                "website": j.company.website if j.company else None,
                "logo_url": j.company.logo_url if j.company else None
            },
            "domain": j.domain or "Engineering",
            "job_type": j.job_type,
            "location": j.location or "Hybrid",
            "ctc": j.ctc or (f"₹{int(j.min_salary / 100000)} - ₹{int(j.max_salary / 100000)} LPA" if j.min_salary and j.max_salary else "Competitive"),
            "min_cgpa": float(j.min_cgpa) if j.min_cgpa else 0.0,
            "eligible_branches": [b.strip() for b in (j.eligible_branches or "").split(",") if b.strip()],
            "eligible_batch_years": [b.strip() for b in (j.eligible_batch_years or "").split(",") if b.strip()],
            "deadline": j.deadline.strftime("%b %d, %Y") if j.deadline else None,
            "is_deadline_passed": j.deadline < datetime.now(timezone.utc) if j.deadline else False,
            "skills": skills_summary,
            "applications_count": len(j.applications),
            "has_applied": j.id in applied_job_ids,
            "match": match_info
        }
        results.append(item)

    # If student is logged in, sort primarily by match score
    if student:
        results.sort(key=lambda x: (x["match"]["overall_match"] if x.get("match") else 0), reverse=True)

    return api_response(
        message="Job listings retrieved successfully.",
        data={
            "total": len(results),
            "jobs": results
        },
        status_code=200
    )


@jobs_bp.route("/<int:job_id>", methods=["GET"])
def get_job_details(job_id):
    """
    Returns full details for a specific job, including prioritized skills,
    eligibility criteria, company information, and student explainable match breakdown.
    """
    job = Job.query.get(job_id)
    if not job or job.status != "Published":
        return error_response("Job posting not found or not published.", 404)

    student = get_current_student_optional()

    # Prioritized skills
    critical_skills = []
    important_skills = []
    preferred_skills = []
    for js in job.required_skills:
        if not js.skill:
            continue
        p = (js.priority or "Important").capitalize()
        skill_payload = {
            "id": js.skill.id,
            "name": js.skill.name,
            "category": js.skill.category,
            "priority": p,
            "min_proficiency": js.min_proficiency
        }
        if p == "Critical":
            critical_skills.append(skill_payload)
        elif p == "Preferred":
            preferred_skills.append(skill_payload)
        else:
            important_skills.append(skill_payload)

    # Check student application status & explainable match
    has_applied = False
    application_data = None
    match_info = None

    if student:
        match_info = calculate_job_match(student, job)
        existing_app = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
        if existing_app:
            has_applied = True
            application_data = {
                "id": existing_app.id,
                "current_status": existing_app.current_status,
                "applied_at": existing_app.applied_at.strftime("%b %d, %Y %I:%M %p") if existing_app.applied_at else "Recently",
                "history": [
                    {
                        "status": h.status,
                        "notes": h.notes,
                        "time": h.created_at.strftime("%b %d, %Y %I:%M %p") if h.created_at else None
                    }
                    for h in existing_app.status_history
                ]
            }

    data = {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "company": {
            "id": job.company.id if job.company else None,
            "name": job.company.name if job.company else "Top Recruiter",
            "industry": job.company.industry if job.company else "Technology",
            "website": job.company.website if job.company else None,
            "location": job.company.location if job.company else None,
            "description": job.company.description if job.company else None
        },
        "domain": job.domain or "Engineering",
        "job_type": job.job_type,
        "location": job.location or "Hybrid",
        "ctc": job.ctc or (f"₹{int(job.min_salary / 100000)} - ₹{int(job.max_salary / 100000)} LPA" if job.min_salary and job.max_salary else "Competitive"),
        "min_cgpa": float(job.min_cgpa) if job.min_cgpa else 0.0,
        "eligible_branches": [b.strip() for b in (job.eligible_branches or "").split(",") if b.strip()],
        "eligible_batch_years": [b.strip() for b in (job.eligible_batch_years or "").split(",") if b.strip()],
        "deadline": job.deadline.strftime("%b %d, %Y %I:%M %p") if job.deadline else None,
        "is_deadline_passed": job.deadline < datetime.now(timezone.utc) if job.deadline else False,
        "skills": {
            "critical": critical_skills,
            "important": important_skills,
            "preferred": preferred_skills
        },
        "has_applied": has_applied,
        "application": application_data,
        "match": match_info
    }

    return api_response(message="Job details retrieved.", data=data, status_code=200)


@jobs_bp.route("/<int:job_id>/apply", methods=["POST"])
@student_required
def apply_to_job(current_user, job_id):
    """
    Submits an application for the specified job.
    Attaches student's primary resume, records initial status APPLIED,
    and creates audit entry in ApplicationStatusHistory.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    job = Job.query.get(job_id)
    if not job or job.status != "Published":
        return error_response("This job opening is not available for applications.", 404)

    # 1. Check Deadline
    if job.deadline and job.deadline < datetime.now(timezone.utc):
        return error_response("The application deadline for this job posting has passed.", 400)

    # 2. Check Duplicate Application
    existing = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
    if existing:
        return error_response("You have already applied to this job opening.", 409)

    # 3. Check Eligibility (Allow apply with warning or block if strict)
    match_data = calculate_job_match(student, job)
    eligibility = match_data["eligibility"]
    if not eligibility["is_eligible"]:
        # Block if CGPA is strictly below
        if not eligibility["cgpa"]["satisfied"]:
            return error_response(
                f"Application rejected due to eligibility criteria: Your CGPA ({eligibility['cgpa']['student_value']}) is below the required minimum ({eligibility['cgpa']['required_min']}).",
                400
            )

    # 4. Attach primary resume
    primary_resume = next((r for r in student.resumes if r.is_primary), student.resumes[-1] if student.resumes else None)

    # 5. Create Application
    application = Application(
        student_id=student.id,
        job_id=job.id,
        resume_id=primary_resume.id if primary_resume else None,
        current_status="APPLIED"
    )
    db.session.add(application)
    db.session.flush()

    # 6. Audit History Log
    status_history = ApplicationStatusHistory(
        application_id=application.id,
        status="APPLIED",
        notes="Application submitted by student.",
        changed_by_user_id=current_user.id
    )
    db.session.add(status_history)
    db.session.commit()

    return api_response(
        message=f"Application for '{job.title}' submitted successfully!",
        data={
            "application_id": application.id,
            "status": application.current_status,
            "applied_at": application.applied_at.strftime("%b %d, %Y %I:%M %p"),
            "resume_attached": primary_resume.file_name if primary_resume else "None (No resume on file)"
        },
        status_code=201
    )

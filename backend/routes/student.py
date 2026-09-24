"""
Student Module Routes.
Provides Profile APIs, Skills management, Projects CRUD, and Dashboard aggregation.
Guarded strictly by @student_required.
"""
import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, request
from werkzeug.utils import secure_filename

from backend.config import Config
from backend.extensions import db
from backend.models.user import Student
from backend.models.student import StudentPreference, Project
from backend.models.skill import Skill, StudentSkill
from backend.models.job import Job
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.notification import Notification
from backend.models.application import Application, Feedback
from backend.models.assessment import Assessment, AssessmentQuestion, AssessmentAttempt
from backend.models.resume import Resume, ResumeAnalysis
from backend.models.placement import Alumni
from backend.services.resume_analyzer import RuleBasedResumeAnalyzer
from backend.services.recommendation_engine import analyze_skill_gap, get_supported_roles
from backend.services.placement_intelligence import PlacementIntelligenceService
from backend.utils.auth import student_required
from backend.utils.response import api_response, error_response

student_bp = Blueprint("student", __name__, url_prefix="/api/students")


def calculate_profile_completion(student):
    """
    Computes profile completeness score (0 to 100%) based on filled fields:
    - Basic Identity (first_name, last_name, roll_number, department, batch_year) [20%]
    - Academic CGPA [15%]
    - Contact Info (phone, gender) [10%]
    - Skills (at least 1 skill: 10%, >=3 skills: 20%) [20%]
    - Projects (at least 1 project: 15%) [15%]
    - Career Preferences (preferred domain or roles) [10%]
    - Experience / Certifications [10%]
    """
    score = 0

    # Basic Identity (20)
    if student.first_name and student.last_name and student.roll_number and student.department and student.batch_year:
        score += 20

    # CGPA (15)
    if student.cgpa is not None:
        score += 15

    # Contact Info (10)
    if student.phone:
        score += 5
    if student.gender:
        score += 5

    # Skills (20)
    skill_count = len(student.student_skills)
    if skill_count >= 3:
        score += 20
    elif skill_count >= 1:
        score += 10

    # Projects (15)
    if len(student.projects) >= 1:
        score += 15

    # Career Preferences (10)
    pref = student.preferences
    if pref and (pref.preferred_domain or pref.preferred_roles):
        score += 10

    # Experience & Certifications (10)
    if student.certifications or student.experience:
        score += 10

    return min(score, 100)


def calculate_placement_readiness(student, completion_score, resume_score):
    """
    Calculates overall placement readiness index (0 - 100%):
    - Profile Completeness: 25%
    - CGPA weight: 25% (normalized against 10.0 scale)
    - Practical Skills depth: 25% (min 5 skills for max score)
    - Projects portfolio: 25% (min 2 projects for max score)
    """
    # 1. Profile Completeness (25 pts)
    comp_pts = (completion_score / 100.0) * 25.0

    # 2. CGPA (25 pts)
    cgpa_val = float(student.cgpa) if student.cgpa is not None else 6.0
    cgpa_pts = min(25.0, (cgpa_val / 10.0) * 25.0)

    # 3. Skills portfolio (25 pts)
    skill_count = len(student.student_skills)
    skills_pts = min(25.0, (skill_count / 5.0) * 25.0)

    # 4. Projects (25 pts)
    proj_count = len(student.projects)
    proj_pts = min(25.0, (proj_count / 2.0) * 25.0)

    total = comp_pts + cgpa_pts + skills_pts + proj_pts
    return round(total, 1)


# ============================================================================
# 1. STUDENT PROFILE ENDPOINTS
# ============================================================================

@student_bp.route("/profile", methods=["GET"])
@student_required
def get_profile(current_user):
    """
    Retrieves the authenticated student's full profile, preferences, and completion metrics.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    pref = student.preferences
    completion = calculate_profile_completion(student)

    data = {
        "id": student.id,
        "roll_number": student.roll_number,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "full_name": f"{student.first_name} {student.last_name}".strip(),
        "email": current_user.email,
        "department": student.department,
        "degree": student.degree,
        "batch_year": student.batch_year,
        "cgpa": float(student.cgpa) if student.cgpa is not None else None,
        "phone": student.phone,
        "gender": student.gender,
        "certifications": student.certifications,
        "experience": student.experience,
        "preferences": {
            "preferred_domain": pref.preferred_domain if pref else None,
            "preferred_roles": pref.preferred_roles if pref else None,
            "preferred_locations": pref.preferred_locations if pref else None,
            "expected_min_salary": float(pref.expected_min_salary) if pref and pref.expected_min_salary else None,
            "job_type_preference": pref.job_type_preference if pref else "Both",
            "willing_to_relocate": pref.willing_to_relocate if pref else True
        },
        "stats": {
            "skills_count": len(student.student_skills),
            "projects_count": len(student.projects),
            "applications_count": len(student.applications),
            "profile_completion": completion
        }
    }

    return api_response(message="Student profile retrieved successfully.", data=data, status_code=200)


@student_bp.route("/profile", methods=["PUT"])
@student_required
def update_profile(current_user):
    """
    Updates student personal, academic, and employment preference fields.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    body = request.get_json(silent=True) or {}

    # Update basic profile fields if provided
    if "first_name" in body and body["first_name"].strip():
        student.first_name = body["first_name"].strip()
    if "last_name" in body and body["last_name"].strip():
        student.last_name = body["last_name"].strip()
    if "department" in body and body["department"].strip():
        student.department = body["department"].strip()
    if "degree" in body and body["degree"].strip():
        student.degree = body["degree"].strip()
    if "batch_year" in body:
        try:
            student.batch_year = int(body["batch_year"])
        except (ValueError, TypeError):
            pass
    if "cgpa" in body:
        try:
            student.cgpa = float(body["cgpa"]) if body["cgpa"] is not None else None
        except (ValueError, TypeError):
            pass
    if "phone" in body:
        student.phone = str(body["phone"]).strip() or None
    if "gender" in body:
        student.gender = str(body["gender"]).strip() or None
    if "certifications" in body:
        student.certifications = str(body["certifications"]).strip() or None
    if "experience" in body:
        student.experience = str(body["experience"]).strip() or None

    # Update or initialize preferences
    pref = student.preferences
    if not pref:
        pref = StudentPreference(student_id=student.id)
        db.session.add(pref)

    if "preferred_domain" in body:
        pref.preferred_domain = str(body["preferred_domain"]).strip() or None
    if "preferred_roles" in body:
        pref.preferred_roles = str(body["preferred_roles"]).strip() or None
    if "preferred_locations" in body:
        pref.preferred_locations = str(body["preferred_locations"]).strip() or None
    if "expected_min_salary" in body:
        try:
            pref.expected_min_salary = float(body["expected_min_salary"]) if body["expected_min_salary"] is not None else None
        except (ValueError, TypeError):
            pass
    if "job_type_preference" in body:
        pref.job_type_preference = str(body["job_type_preference"]).strip() or "Both"
    if "willing_to_relocate" in body:
        pref.willing_to_relocate = bool(body["willing_to_relocate"])

    db.session.commit()

    return api_response(message="Student profile updated successfully.", status_code=200)


# ============================================================================
# 2. STUDENT SKILLS ENDPOINTS
# ============================================================================

@student_bp.route("/skills", methods=["GET"])
@student_required
def get_skills(current_user):
    """
    Returns list of skills attached to the student.
    """
    student = current_user.student_profile
    skills_list = [
        {
            "id": ss.id,
            "skill_id": ss.skill.id,
            "name": ss.skill.name,
            "category": ss.skill.category,
            "proficiency_level": ss.proficiency_level,
            "is_verified": ss.is_verified
        }
        for ss in student.student_skills
    ]
    return api_response(message="Skills retrieved.", data={"skills": skills_list}, status_code=200)


@student_bp.route("/skills", methods=["POST"])
@student_required
def add_skill(current_user):
    """
    Attaches a skill to the student with a proficiency level.
    Finds or creates Skill catalog item by name.
    """
    student = current_user.student_profile
    body = request.get_json(silent=True) or {}

    skill_name = str(body.get("name") or "").strip()
    if not skill_name:
        return error_response("Skill name is required.", 400)

    category = str(body.get("category") or "Technical").strip()
    proficiency = str(body.get("proficiency_level") or "Intermediate").strip()

    # Find or create skill in catalog
    skill = Skill.query.filter(db.func.lower(Skill.name) == skill_name.lower()).first()
    if not skill:
        skill = Skill(name=skill_name, category=category)
        db.session.add(skill)
        db.session.flush()

    # Check if student already has this skill
    existing = StudentSkill.query.filter_by(student_id=student.id, skill_id=skill.id).first()
    if existing:
        existing.proficiency_level = proficiency
        db.session.commit()
        return api_response(
            message=f"Proficiency for skill '{skill.name}' updated.",
            data={
                "id": existing.id,
                "skill_id": skill.id,
                "name": skill.name,
                "proficiency_level": existing.proficiency_level
            },
            status_code=200
        )

    # Add new skill link
    new_skill_link = StudentSkill(
        student_id=student.id,
        skill_id=skill.id,
        proficiency_level=proficiency
    )
    db.session.add(new_skill_link)
    db.session.commit()

    return api_response(
        message=f"Skill '{skill.name}' added successfully.",
        data={
            "id": new_skill_link.id,
            "skill_id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "proficiency_level": new_skill_link.proficiency_level
        },
        status_code=201
    )


@student_bp.route("/skills/<int:id>", methods=["DELETE"])
@student_required
def delete_skill(current_user, id):
    """
    Removes a skill from the student's profile.
    """
    student = current_user.student_profile
    student_skill = db.session.get(StudentSkill, id)

    if not student_skill or student_skill.student_id != student.id:
        return error_response("Skill not found on your profile.", 404)

    skill_name = student_skill.skill.name if student_skill.skill else "Skill"
    db.session.delete(student_skill)
    db.session.commit()

    return api_response(message=f"Skill '{skill_name}' removed from your profile.", status_code=200)


# ============================================================================
# 3. STUDENT PROJECTS CRUD ENDPOINTS
# ============================================================================

@student_bp.route("/projects", methods=["GET"])
@student_required
def get_projects(current_user):
    """
    Lists all portfolio projects completed by the student.
    """
    student = current_user.student_profile
    projects_list = [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "technologies_used": p.technologies_used,
            "github_url": p.github_url,
            "live_url": p.live_url,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None
        }
        for p in student.projects
    ]
    return api_response(message="Projects retrieved.", data={"projects": projects_list}, status_code=200)


@student_bp.route("/projects", methods=["POST"])
@student_required
def create_project(current_user):
    """
    Creates a new project on the student's portfolio.
    """
    student = current_user.student_profile
    body = request.get_json(silent=True) or {}

    title = str(body.get("title") or "").strip()
    if not title:
        return error_response("Project title is required.", 400)

    # Parse dates safely if provided
    start_date = None
    if body.get("start_date"):
        try:
            start_date = datetime.strptime(body["start_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    end_date = None
    if body.get("end_date"):
        try:
            end_date = datetime.strptime(body["end_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    project = Project(
        student_id=student.id,
        title=title,
        description=str(body.get("description") or "").strip() or None,
        technologies_used=str(body.get("technologies_used") or "").strip() or None,
        github_url=str(body.get("github_url") or "").strip() or None,
        live_url=str(body.get("live_url") or "").strip() or None,
        start_date=start_date,
        end_date=end_date
    )
    db.session.add(project)
    db.session.commit()

    return api_response(
        message="Project created successfully.",
        data={
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "technologies_used": project.technologies_used,
            "github_url": project.github_url,
            "live_url": project.live_url
        },
        status_code=201
    )


@student_bp.route("/projects/<int:id>", methods=["PUT"])
@student_required
def update_project(current_user, id):
    """
    Updates an existing project belonging to the student.
    """
    student = current_user.student_profile
    project = db.session.get(Project, id)

    if not project or project.student_id != student.id:
        return error_response("Project not found.", 404)

    body = request.get_json(silent=True) or {}

    if "title" in body and body["title"].strip():
        project.title = body["title"].strip()
    if "description" in body:
        project.description = str(body["description"]).strip() or None
    if "technologies_used" in body:
        project.technologies_used = str(body["technologies_used"]).strip() or None
    if "github_url" in body:
        project.github_url = str(body["github_url"]).strip() or None
    if "live_url" in body:
        project.live_url = str(body["live_url"]).strip() or None

    db.session.commit()

    return api_response(message="Project updated successfully.", status_code=200)


@student_bp.route("/projects/<int:id>", methods=["DELETE"])
@student_required
def delete_project(current_user, id):
    """
    Deletes a project from the student's portfolio.
    """
    student = current_user.student_profile
    project = db.session.get(Project, id)

    if not project or project.student_id != student.id:
        return error_response("Project not found.", 404)

    db.session.delete(project)
    db.session.commit()

    return api_response(message="Project deleted successfully.", status_code=200)


# ============================================================================
# 4. STUDENT DASHBOARD AGGREGATION ENDPOINT
# ============================================================================

@student_bp.route("/dashboard", methods=["GET"])
@student_required
def get_dashboard(current_user):
    """
    Consolidated dashboard metric endpoint returning:
    - Student name
    - Profile completion %
    - Resume score
    - Placement readiness index
    - Recommended jobs
    - Upcoming workshops
    - Recent notifications
    - Application status summary
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    completion_score = calculate_profile_completion(student)

    # Resume score (0 if no resume or pending analysis)
    resume_score = 0
    if student.resumes:
        primary_resume = next((r for r in student.resumes if r.is_primary), student.resumes[-1])
        if primary_resume and primary_resume.analysis and primary_resume.analysis.overall_score:
            resume_score = float(primary_resume.analysis.overall_score)

    placement_readiness = calculate_placement_readiness(student, completion_score, resume_score)

    # Recommended jobs (Open jobs matching department or latest open postings)
    # Recommended jobs (Open or Published jobs matching department or latest open postings)
    open_jobs = Job.query.filter(Job.status.in_(["Open", "Published"])).order_by(Job.created_at.desc()).limit(5).all()
    recommended_jobs = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company.name if j.company else "Top Company",
            "job_type": j.job_type,
            "location": j.location or "Hybrid",
            "min_cgpa": float(j.min_cgpa) if j.min_cgpa is not None else 0.0,
            "deadline": j.deadline.strftime("%Y-%m-%d") if j.deadline else None,
            "skills": [js.skill.name for js in j.required_skills[:3] if js.skill]
        }
        for j in open_jobs
    ]

    # Upcoming Workshops
    workshops = Workshop.query.order_by(Workshop.start_time.asc()).limit(6).all()
    reg_workshop_ids = {r.workshop_id for r in student.workshop_registrations} if student.workshop_registrations else set()
    upcoming_workshops = [
        {
            "id": w.id,
            "title": w.title,
            "instructor": f"{w.instructor.first_name} {w.instructor.last_name}" if w.instructor else "Industry Expert",
            "company": w.company.name if w.company else None,
            "start_time": w.start_time.strftime("%b %d, %Y %I:%M %p") if w.start_time else "TBA",
            "venue_or_link": w.venue_or_link or "Virtual",
            "is_registered": w.id in reg_workshop_ids
        }
        for w in workshops
    ]

    # Recent Notifications
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    recent_notifications = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "time": n.created_at.strftime("%b %d, %I:%M %p") if n.created_at else "Recently"
        }
        for n in notifs
    ]

    # Application Status Breakdown
    apps = student.applications
    app_status_counts = {
        "total": len(apps),
        "applied": sum(1 for a in apps if (a.current_status or "").upper() == "APPLIED"),
        "shortlisted": sum(1 for a in apps if (a.current_status or "").upper() in ["SHORTLISTED", "ASSESSMENT"]),
        "interview": sum(1 for a in apps if "INTERVIEW" in (a.current_status or "").upper()),
        "selected": sum(1 for a in apps if (a.current_status or "").upper() in ["SELECTED", "OFFER RELEASED"]),
        "rejected": sum(1 for a in apps if (a.current_status or "").upper() == "REJECTED")
    }

    recent_applications = [
        {
            "id": a.id,
            "job_title": a.job.title if a.job else "Role",
            "company": a.job.company.name if a.job and a.job.company else "Company",
            "status": a.current_status,
            "applied_at": a.applied_at.strftime("%b %d, %Y") if a.applied_at else "Recent"
        }
        for a in apps[:5]
    ]

    dashboard_data = {
        "student_name": f"{student.first_name} {student.last_name}".strip(),
        "roll_number": student.roll_number,
        "department": student.department,
        "batch_year": student.batch_year,
        "profile_completion": completion_score,
        "resume_score": resume_score,
        "placement_readiness": placement_readiness,
        "skills_count": len(student.student_skills),
        "projects_count": len(student.projects),
        "recommended_jobs": recommended_jobs,
        "upcoming_workshops": upcoming_workshops,
        "recent_notifications": recent_notifications,
        "applications": {
            "counts": app_status_counts,
            "recent": recent_applications
        }
    }

    return api_response(message="Student dashboard data retrieved.", data=dashboard_data, status_code=200)


@student_bp.route("/applications", methods=["GET"])
@student_required
def get_student_applications(current_user):
    """
    Returns all job applications submitted by the logged-in student,
    including company info, current status, and full audit timeline.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()

    results = []
    for a in applications:
        job = a.job
        results.append({
            "id": a.id,
            "job": {
                "id": job.id if job else None,
                "title": job.title if job else "Opening",
                "job_type": job.job_type if job else "Full-time",
                "location": job.location if job else "Hybrid",
                "ctc": job.ctc if job else "Competitive",
                "domain": job.domain if job else "Engineering",
                "company": {
                    "id": job.company.id if job and job.company else None,
                    "name": job.company.name if job and job.company else "Top Company"
                }
            },
            "resume_attached": a.resume.file_name if a.resume else "None",
            "status": a.current_status,
            "current_status": a.current_status,
            "applied_at": a.applied_at.strftime("%b %d, %Y %I:%M %p") if a.applied_at else "Recently",
            "timeline": [
                {
                    "from_status": h.notes.split("from ")[1].split(" to")[0] if "from " in (h.notes or "") else "APPLIED",
                    "to_status": h.status,
                    "status": h.status,
                    "notes": h.notes,
                    "changed_by_role": "recruiter",
                    "changed_at": h.created_at.isoformat() if h.created_at else None,
                    "time": h.created_at.strftime("%b %d, %Y %I:%M %p") if h.created_at else None
                }
                for h in a.status_history
            ],
            "status_history": [
                {
                    "status": h.status,
                    "notes": h.notes,
                    "time": h.created_at.strftime("%b %d, %Y %I:%M %p") if h.created_at else None
                }
                for h in a.status_history
            ]
        })

    return api_response(
        message="Student applications retrieved successfully.",
        data={
            "total": len(results),
            "applications": results
        },
        status_code=200
    )


# ============================================================================
# 5. STUDENT RESUME INTELLIGENCE & SKILL-GAP ENDPOINTS
# ============================================================================

@student_bp.route("/resume", methods=["POST"])
@student_required
def upload_and_analyze_resume(current_user):
    """
    Uploads a student PDF resume, validates format, securely saves the file,
    extracts structured candidate data using PyMuPDF, scores the resume
    against deterministic rubric criteria, and executes skill-gap analysis.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    # 1. Check if file is in request
    if "file" not in request.files:
        return error_response("No resume file uploaded. Please choose a PDF file.", 400)

    file = request.files["file"]
    if not file or file.filename == "":
        return error_response("Empty filename provided. Please select a valid PDF file.", 400)

    # 2. Validate file extension
    filename = file.filename
    if not filename.lower().endswith(".pdf"):
        return error_response("Invalid file extension. Only PDF documents (.pdf) are accepted.", 400)

    # 3. Check MIME type & PDF Magic Bytes (%PDF-)
    content_type = file.content_type or ""
    header_bytes = file.read(5)
    file.seek(0)
    if not header_bytes.startswith(b"%PDF-"):
        return error_response("Invalid file format. The uploaded file is not a valid PDF document.", 400)

    # 4. Enforce file size limit (5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size == 0:
        return error_response("Uploaded file is empty (0 bytes).", 400)

    max_size = getattr(Config, "MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
    if file_size > max_size:
        return error_response(f"File size exceeds maximum allowed limit ({max_size // (1024 * 1024)}MB).", 413)

    # 5. Generate safe unique filename and destination
    original_safe_name = secure_filename(filename) or "student_resume.pdf"
    unique_suffix = f"stu_{student.id}_{uuid.uuid4().hex[:8]}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
    upload_dir = Config.UPLOAD_FOLDER
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination_path = upload_dir / unique_suffix

    # Save to disk
    try:
        file.save(str(destination_path))
    except Exception as e:
        return error_response("Failed to save uploaded resume securely to disk.", 500, str(e))

    # 6. Parse and extract text using PyMuPDF
    analyzer = RuleBasedResumeAnalyzer()
    target_role = request.form.get("target_role") or (student.preferences.preferred_roles if student.preferences else None) or "Software Engineer"
    
    supported_roles = get_supported_roles()
    if target_role not in supported_roles:
        target_role = "Software Engineer"

    try:
        parsed_data = analyzer.analyze_resume_pipeline(str(destination_path), target_role=target_role)
    except ValueError as e:
        # If parsing or PDF verification failed, clean up disk storage safely
        if destination_path.exists():
            destination_path.unlink()
        return error_response(f"PDF Analysis Error: {str(e)}", 400)
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        return error_response("Failed to extract readable content from PDF.", 500, str(e))

    # 7. Execute Skill-Gap Analysis
    extracted_skill_names = [s["name"] for s in parsed_data["skills"]]
    gap_analysis = analyze_skill_gap(extracted_skill_names, target_role=target_role)

    # 8. Calculate Deterministic Rubric Score
    score_result = analyzer.score_resume(parsed_data, target_role_score=gap_analysis["match_score"])

    # 9. Update Database Models
    # Mark existing resumes as non-primary
    for prev_resume in student.resumes:
        prev_resume.is_primary = False

    next_version = len(student.resumes) + 1
    new_resume = Resume(
        student_id=student.id,
        file_path=unique_suffix,  # Secure internal token name, never server path
        file_name=original_safe_name,
        file_size=file_size,
        is_primary=True,
        version=next_version
    )
    db.session.add(new_resume)
    db.session.flush()

    new_analysis = ResumeAnalysis(
        resume_id=new_resume.id,
        overall_score=score_result["overall_score"],
        parsed_skills_json=json.dumps(parsed_data["skills"]),
        skill_gap_json=json.dumps(gap_analysis),
        strengths_json=json.dumps(score_result["strengths"]),
        improvements_json=json.dumps(score_result["improvements"]),
        extracted_text=parsed_data["raw_text"][:8000]  # Store first 8000 chars of parsed text
    )
    db.session.add(new_analysis)

    # Optional: Automatically sync extracted skills into student profile
    sync_skills_param = request.form.get("sync_skills", "false").lower() in ["true", "1", "yes"]
    synced_skills_count = 0
    if sync_skills_param:
        existing_student_skill_ids = set(ss.skill_id for ss in student.student_skills)
        for s in parsed_data["skills"]:
            catalog_skill = Skill.query.filter_by(name=s["name"]).first()
            if not catalog_skill:
                catalog_skill = Skill(name=s["name"], category=s["category"])
                db.session.add(catalog_skill)
                db.session.flush()
            if catalog_skill.id not in existing_student_skill_ids:
                new_stu_skill = StudentSkill(
                    student_id=student.id,
                    skill_id=catalog_skill.id,
                    proficiency_level="Intermediate"
                )
                db.session.add(new_stu_skill)
                existing_student_skill_ids.add(catalog_skill.id)
                synced_skills_count += 1

    db.session.commit()

    response_payload = {
        "resume": {
            "id": new_resume.id,
            "file_name": new_resume.file_name,
            "file_size_kb": round(file_size / 1024, 1),
            "version": new_resume.version,
            "uploaded_at": new_resume.created_at.strftime("%b %d, %Y %I:%M %p")
        },
        "overall_score": score_result["overall_score"],
        "rating_label": score_result["rating_label"],
        "score_breakdown": score_result["score_breakdown"],
        "target_role": target_role,
        "supported_roles": supported_roles,
        "skill_gap": gap_analysis,
        "extracted_skills": parsed_data["skills"],
        "education": parsed_data["education"],
        "projects": parsed_data["projects"],
        "experience": parsed_data["experience"],
        "contact": parsed_data["contact"],
        "strengths": score_result["strengths"],
        "improvements": score_result["improvements"],
        "synced_skills_count": synced_skills_count
    }

    return api_response(
        message=f"Resume uploaded and analyzed successfully! Scored {score_result['overall_score']}/100.",
        data=response_payload,
        status_code=201
    )


@student_bp.route("/resume-analysis", methods=["GET"])
@student_required
def get_resume_analysis(current_user):
    """
    Retrieves the latest / primary resume analysis for the logged-in student.
    Supports dynamic target_role parameter (?target_role=...) to recalculate
    skill-gap analysis on demand without re-uploading the resume file.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    supported_roles = get_supported_roles()

    # Find primary or latest resume
    primary_resume = next((r for r in student.resumes if r.is_primary), student.resumes[-1] if student.resumes else None)
    if not primary_resume or not primary_resume.analysis:
        return api_response(
            message="No resume analysis found.",
            data={
                "has_resume": False,
                "supported_roles": supported_roles
            },
            status_code=200
        )

    analysis = primary_resume.analysis

    # Parse stored JSON metrics
    try:
        parsed_skills = json.loads(analysis.parsed_skills_json) if analysis.parsed_skills_json else []
    except Exception:
        parsed_skills = []

    try:
        stored_gap = json.loads(analysis.skill_gap_json) if analysis.skill_gap_json else {}
    except Exception:
        stored_gap = {}

    try:
        strengths = json.loads(analysis.strengths_json) if analysis.strengths_json else []
    except Exception:
        strengths = []

    try:
        improvements = json.loads(analysis.improvements_json) if analysis.improvements_json else []
    except Exception:
        improvements = []

    # Dynamic target role evaluation if specified in query params
    target_role = request.args.get("target_role")
    if target_role and target_role in supported_roles:
        extracted_names = [s["name"] for s in parsed_skills]
        gap_analysis = analyze_skill_gap(extracted_names, target_role=target_role)
    elif stored_gap:
        gap_analysis = stored_gap
        target_role = gap_analysis.get("target_role", "Software Engineer")
    else:
        extracted_names = [s["name"] for s in parsed_skills]
        gap_analysis = analyze_skill_gap(extracted_names, target_role="Software Engineer")
        target_role = "Software Engineer"

    # Re-score if role changed dynamically
    overall_score = float(analysis.overall_score) if analysis.overall_score is not None else 0.0
    analyzer = RuleBasedResumeAnalyzer()
    
    if analysis.extracted_text:
        sections = analyzer.parse_sections(analysis.extracted_text)
        education = analyzer.extract_education(sections.get("education", "") or analysis.extracted_text)
        projects = analyzer.extract_projects(sections.get("projects", "") or analysis.extracted_text)
        experience = analyzer.extract_experience(sections.get("experience", "") or analysis.extracted_text)
        parsed_data = {
            "raw_text": analysis.extracted_text,
            "sections": sections,
            "contact": {"email": current_user.email},
            "skills": parsed_skills,
            "education": education,
            "projects": projects,
            "experience": experience
        }
    else:
        parsed_data = {
            "raw_text": "",
            "sections": {"education": "found", "skills": "found", "projects": "found", "experience": "found"},
            "contact": {"email": current_user.email},
            "skills": parsed_skills,
            "education": {"degree": student.degree, "department": student.department, "cgpa": float(student.cgpa) if student.cgpa else None},
            "projects": [],
            "experience": []
        }

    score_result = analyzer.score_resume(parsed_data, target_role_score=gap_analysis["match_score"])

    # If dynamic target role requested, use recalculated overall score, else keep verified DB score
    active_score = score_result["overall_score"] if request.args.get("target_role") else overall_score

    response_payload = {
        "has_resume": True,
        "resume": {
            "id": primary_resume.id,
            "file_name": primary_resume.file_name,
            "file_size_kb": round(primary_resume.file_size / 1024, 1) if primary_resume.file_size else None,
            "version": primary_resume.version,
            "uploaded_at": primary_resume.created_at.strftime("%b %d, %Y %I:%M %p")
        },
        "overall_score": active_score,
        "rating_label": score_result["rating_label"],
        "score_breakdown": score_result["score_breakdown"],
        "target_role": target_role,
        "supported_roles": supported_roles,
        "skill_gap": gap_analysis,
        "extracted_skills": parsed_skills,
        "strengths": strengths or score_result["strengths"],
        "improvements": improvements or score_result["improvements"]
    }

    return api_response(
        message="Resume analysis retrieved successfully.",
        data=response_payload,
        status_code=200
    )


# ============================================================================
# ASSESSMENTS & TESTS (STUDENT VIEW & ATTEMPTS)
# ============================================================================

@student_bp.route("/assessments", methods=["GET"])
@student_required
def list_student_assessments(current_user):
    """
    Lists active assessments available to the student.
    Includes test duration, passing criteria, company details,
    linked job (if applicable), and student's latest attempt status.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    assessments = Assessment.query.filter_by(is_active=True).order_by(Assessment.created_at.desc()).all()
    results = []
    for a in assessments:
        item = a.to_dict(include_questions=False)
        latest_attempt = AssessmentAttempt.query.filter_by(
            assessment_id=a.id, student_id=student.id
        ).order_by(AssessmentAttempt.created_at.desc()).first()

        item["attempt"] = latest_attempt.to_dict() if latest_attempt else None
        results.append(item)

    return api_response(
        message="Available assessments retrieved.",
        data={"assessments": results},
        status_code=200
    )


@student_bp.route("/assessments/<int:assessment_id>", methods=["GET"])
@student_required
def get_assessment_details(current_user, assessment_id):
    """
    Retrieves full details of a specific assessment including questions.
    SECURITY: Correct answers are strictly omitted (include_answer=False).
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    assessment = Assessment.query.filter_by(id=assessment_id, is_active=True).first()
    if not assessment:
        return error_response("Assessment not found or inactive.", 404)

    latest_attempt = AssessmentAttempt.query.filter_by(
        assessment_id=assessment.id, student_id=student.id
    ).order_by(AssessmentAttempt.created_at.desc()).first()

    data = assessment.to_dict(include_questions=True, include_answer=False)
    data["attempt"] = latest_attempt.to_dict() if latest_attempt else None

    return api_response(
        message="Assessment details retrieved.",
        data={"assessment": data},
        status_code=200
    )


@student_bp.route("/assessments/<int:assessment_id>/submit", methods=["POST"])
@student_required
def submit_assessment(current_user, assessment_id):
    """
    Submits candidate answers and triggers server-side auto-grading.
    Calculates marks obtained, percentage, and determines pass/fail status.
    Records AssessmentAttempt and returns instant evaluated feedback.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    assessment = Assessment.query.filter_by(id=assessment_id, is_active=True).first()
    if not assessment:
        return error_response("Assessment not found or inactive.", 404)

    payload = request.get_json() or {}
    answers = payload.get("answers", {})  # Dict of { question_id: selected_option }

    total_marks = 0.0
    obtained_marks = 0.0
    evaluation_details = []

    for q in assessment.questions:
        q_marks = float(q.marks) if q.marks is not None else 1.0
        total_marks += q_marks
        q_id_str = str(q.id)
        student_ans = str(answers.get(q_id_str, "")).strip()
        correct_ans = str(q.correct_answer).strip()

        is_correct = (student_ans.lower() == correct_ans.lower()) if student_ans else False
        marks_awarded = q_marks if is_correct else 0.0
        obtained_marks += marks_awarded

        evaluation_details.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "submitted_answer": student_ans,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "total_question_marks": q_marks
        })

    percentage = round((obtained_marks / total_marks * 100.0), 2) if total_marks > 0 else 0.0
    passing_criterion = float(assessment.passing_score) if assessment.passing_score is not None else 40.0
    passed = percentage >= passing_criterion or obtained_marks >= passing_criterion

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student.id,
        score=obtained_marks,
        passed=passed,
        answers_json=json.dumps(answers),
        completed_at=datetime.now(timezone.utc)
    )
    db.session.add(attempt)
    db.session.commit()

    return api_response(
        message=f"Assessment submitted successfully. You scored {obtained_marks}/{total_marks} ({percentage}%).",
        data={
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "score": obtained_marks,
            "total_marks": total_marks,
            "percentage": percentage,
            "passing_score": passing_criterion,
            "passed": passed,
            "evaluation": evaluation_details
        },
        status_code=200
    )


# ============================================================================
# CANDIDATE FEEDBACK & EVALUATIONS (STUDENT VIEW)
# ============================================================================

@student_bp.route("/feedback", methods=["GET"])
@student_required
def list_student_feedback(current_user):
    """
    Retrieves all constructive feedback entries shared with this student.
    Strictly filters by `is_visible_to_student == True`.
    Internal recruiter notes remain hidden.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    feedbacks = Feedback.query.filter_by(
        target_student_id=student.id,
        is_visible_to_student=True
    ).order_by(Feedback.created_at.desc()).all()

    return api_response(
        message="Interview feedback records retrieved.",
        data={"feedback": [f.to_dict() for f in feedbacks]},
        status_code=200
    )


# ============================================================================
# WORKSHOPS & WEBINARS (STUDENT)
# ============================================================================

@student_bp.route("/workshops", methods=["GET"])
@student_required
def list_student_workshops(current_user):
    """
    Lists all available campus workshops, webinars, and masterclasses.
    Includes registration status and remaining capacity.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    workshops = Workshop.query.order_by(Workshop.start_time.asc()).all()
    registered_workshop_ids = set([
        r.workshop_id for r in WorkshopRegistration.query.filter_by(student_id=student.id).all()
    ])

    results = []
    for w in workshops:
        current_registrations = len(w.registrations)
        results.append({
            "id": w.id,
            "title": w.title,
            "description": w.description,
            "instructor": {
                "name": f"{w.instructor.first_name} {w.instructor.last_name}" if w.instructor else (w.company.name if w.company else "Industry Expert"),
                "company": w.company.name if w.company else "Tech Partner"
            },
            "start_time": w.start_time.strftime("%b %d, %Y %I:%M %p") if w.start_time else None,
            "end_time": w.end_time.strftime("%b %d, %Y %I:%M %p") if w.end_time else None,
            "venue_or_link": w.venue_or_link,
            "max_capacity": w.max_capacity,
            "registered_count": current_registrations,
            "available_seats": max(0, w.max_capacity - current_registrations),
            "is_registered": w.id in registered_workshop_ids
        })

    return api_response(
        message="Available workshops retrieved.",
        data={"total": len(results), "workshops": results},
        status_code=200
    )


@student_bp.route("/workshops/<int:workshop_id>/register", methods=["POST"])
@student_required
def register_for_workshop(current_user, workshop_id):
    """Registers the logged-in student for a technical workshop or webinar."""
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    workshop = Workshop.query.get(workshop_id)
    if not workshop:
        return error_response("Workshop not found.", 404)

    # Check existing registration
    existing = WorkshopRegistration.query.filter_by(
        workshop_id=workshop.id, student_id=student.id
    ).first()
    if existing:
        return error_response("You are already registered for this workshop.", 400)

    # Check capacity
    current_count = len(workshop.registrations)
    if current_count >= workshop.max_capacity:
        return error_response("This workshop has reached maximum capacity.", 400)

    registration = WorkshopRegistration(
        workshop_id=workshop.id,
        student_id=student.id,
        attendance_status="Registered"
    )
    db.session.add(registration)
    db.session.commit()

    return api_response(
        message=f"Successfully registered for '{workshop.title}'.",
        data={
            "workshop_id": workshop.id,
            "title": workshop.title,
            "start_time": workshop.start_time.isoformat() if workshop.start_time else None,
            "venue_or_link": workshop.venue_or_link,
            "attendance_status": registration.attendance_status
        },
        status_code=201
    )


@student_bp.route("/workshops/<int:workshop_id>/register", methods=["DELETE"])
@student_required
def cancel_workshop_registration(current_user, workshop_id):
    """Cancels registration for a workshop."""
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    registration = WorkshopRegistration.query.filter_by(
        workshop_id=workshop_id, student_id=student.id
    ).first()
    if not registration:
        return error_response("Registration not found.", 404)

    db.session.delete(registration)
    db.session.commit()

    return api_response(
        message="Workshop registration cancelled successfully.",
        status_code=200
    )


# ============================================================================
# ALUMNI MENTORS DIRECTORY (STUDENT) - STRICT PRIVACY GUARDRAILS
# ============================================================================

@student_bp.route("/alumni", methods=["GET"])
@student_required
def get_student_alumni(current_user):
    """
    Returns verified alumni mentors for student networking, interview preparation, and mentorship.
    Allows filtering by department, company, mentor_only, and search query.
    PRIVACY GUARDRAIL: Only verified alumni are exposed. Private contact info (email/phone)
    is strictly masked unless the alumnus gave explicit consent (consent_share_contact == True).
    """
    mentor_only = request.args.get("mentor_only", "false").lower() == "true"
    department = request.args.get("department")
    company = request.args.get("company")
    search = request.args.get("search", "").strip().lower()

    query = Alumni.query.filter_by(is_verified=True)
    if mentor_only:
        query = query.filter_by(willing_to_mentor=True)
    if department:
        query = query.filter(Alumni.department.ilike(f"%{department}%"))
    if company:
        query = query.filter(Alumni.current_company.ilike(f"%{company}%"))

    alumni_list = query.order_by(Alumni.graduation_year.desc(), Alumni.name.asc()).all()

    if search:
        alumni_list = [
            a for a in alumni_list
            if search in (a.name or "").lower()
            or search in (a.current_company or "").lower()
            or search in (a.current_role or "").lower()
            or search in (a.department or "").lower()
        ]

    # Mask private contact details unless consent was given
    public_alumni = [a.to_public_dict(include_private=False) for a in alumni_list]

    return api_response(
        message="Verified alumni directory retrieved successfully.",
        data={
            "total": len(public_alumni),
            "alumni": public_alumni
        },
        status_code=200
    )


# ============================================================================
# 11. PLACEMENT INTELLIGENCE: "WHY AM I NOT GETTING SELECTED?"
# ============================================================================

@student_bp.route("/placement-intelligence", methods=["GET"])
@student_bp.route("/why-not-selected", methods=["GET"])
@student_required
def get_placement_intelligence_diagnosis(current_user):
    """
    Signature diagnostic endpoint for students:
    Answers 'Why Am I Not Getting Selected?' by analyzing application funnels,
    recurring skill gaps across applied jobs, verified employer feedback,
    ATS score, and tailored upskilling recommendations.
    """
    student = current_user.student_profile
    if not student:
        return error_response("Student profile not found.", 404)

    diagnosis = PlacementIntelligenceService.diagnose_selection_bottlenecks(student.id)
    if diagnosis.get("status") == "error":
        return error_response(diagnosis.get("message", "Failed to compute diagnosis"), 400)

    return api_response(
        message="Placement intelligence diagnostic evaluation generated successfully.",
        data=diagnosis["data"],
        status_code=200
    )




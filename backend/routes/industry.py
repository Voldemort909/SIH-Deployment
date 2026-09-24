"""
Industry Expert Module Routes.
Provides job creation, editing, applicant review, and status workflow management.
Guarded strictly by @industry_required.
"""
import json
from datetime import datetime, timezone
from flask import Blueprint, request

from backend.extensions import db
from backend.models.job import Job
from backend.models.company import Company
from backend.models.skill import Skill, JobSkill, StudentSkill
from backend.models.application import Application, ApplicationStatusHistory, Feedback
from backend.models.assessment import Assessment, AssessmentQuestion, AssessmentAttempt
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.user import IndustryExpert, Student, User
from backend.services.job_matcher import calculate_job_match
from backend.utils.auth import industry_required
from backend.utils.response import api_response, error_response

industry_bp = Blueprint("industry", __name__, url_prefix="/api/industry")

ALLOWED_STATUSES = [
    "APPLIED", "UNDER_REVIEW", "SHORTLISTED", "ASSESSMENT", "INTERVIEW", "SELECTED", "REJECTED"
]


@industry_bp.route("/jobs", methods=["POST"])
@industry_required
def create_job(current_user):
    """
    Creates a new job listing with prioritized skills.
    Status starts in 'Pending Approval' and requires administrator review before publishing.
    """
    expert = current_user.industry_profile
    if not expert:
        return error_response("Industry profile not found.", 404)

    data = request.get_json() or {}

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    job_type = data.get("job_type", "Full-time").strip()

    if not title or not description:
        return error_response("Job title and description are required fields.", 400)

    # Ensure company is associated with expert
    company = expert.company
    if not company:
        # Create or link default company
        company = Company.query.filter_by(name=expert.company_name or "Partner Organization").first()
        if not company:
            company = Company(
                name=expert.company_name or "Partner Organization",
                industry_type="Technology",
                location=data.get("location")
            )
            db.session.add(company)
            db.session.flush()

    # Parse deadline if provided
    deadline_dt = None
    if data.get("deadline"):
        try:
            deadline_dt = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00"))
        except ValueError:
            pass

    # Create Job listing (initially Pending Approval)
    job = Job(
        company_id=company.id,
        posted_by_expert_id=expert.id,
        title=title,
        description=description,
        job_type=job_type,
        location=data.get("location", "Hybrid"),
        domain=data.get("domain", "Software Engineering"),
        ctc=data.get("ctc", "Competitive"),
        min_cgpa=float(data.get("min_cgpa", 0.0)),
        eligible_branches=",".join([b.strip() for b in data.get("eligible_branches", [])]) if isinstance(data.get("eligible_branches"), list) else data.get("eligible_branches", ""),
        eligible_batch_years=",".join([str(y).strip() for y in data.get("eligible_batch_years", [])]) if isinstance(data.get("eligible_batch_years"), list) else str(data.get("eligible_batch_years", "")),
        deadline=deadline_dt,
        status="Pending Approval"
    )
    db.session.add(job)
    db.session.flush()

    # Add prioritized skills
    skills_data = data.get("skills", [])
    added_skills = []
    for s in skills_data:
        s_name = s.get("name", "").strip()
        if not s_name:
            continue
        priority = (s.get("priority") or "Important").capitalize()
        if priority not in ["Critical", "Important", "Preferred"]:
            priority = "Important"
        proficiency = s.get("min_proficiency", "Intermediate")

        # Find or create skill
        catalog_skill = Skill.query.filter_by(name=s_name).first()
        if not catalog_skill:
            catalog_skill = Skill(name=s_name, category="Technical")
            db.session.add(catalog_skill)
            db.session.flush()

        job_skill = JobSkill(
            job_id=job.id,
            skill_id=catalog_skill.id,
            priority=priority,
            is_mandatory=(priority in ["Critical", "Important"]),
            min_proficiency=proficiency
        )
        db.session.add(job_skill)
        added_skills.append({"name": s_name, "priority": priority})

    db.session.commit()

    return api_response(
        message="Job listing submitted successfully! It is currently Pending Approval by an administrator.",
        data={
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "skills": added_skills,
            "created_at": job.created_at.strftime("%b %d, %Y %I:%M %p")
        },
        status_code=201
    )


@industry_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@industry_required
def update_job(current_user, job_id):
    """
    Updates an existing job posting.
    If already published, changes require re-moderation unless minor.
    """
    expert = current_user.industry_profile
    job = Job.query.get(job_id)
    if not job or job.posted_by_expert_id != expert.id:
        return error_response("Job posting not found or you do not have permission to modify it.", 404)

    data = request.get_json() or {}

    if "title" in data: job.title = data["title"].strip()
    if "description" in data: job.description = data["description"].strip()
    if "job_type" in data: job.job_type = data["job_type"].strip()
    if "location" in data: job.location = data["location"].strip()
    if "domain" in data: job.domain = data["domain"].strip()
    if "ctc" in data: job.ctc = data["ctc"].strip()
    if "min_cgpa" in data: job.min_cgpa = float(data["min_cgpa"])
    if "eligible_branches" in data:
        job.eligible_branches = ",".join(data["eligible_branches"]) if isinstance(data["eligible_branches"], list) else data["eligible_branches"]
    if "eligible_batch_years" in data:
        job.eligible_batch_years = ",".join([str(y) for y in data["eligible_batch_years"]]) if isinstance(data["eligible_batch_years"], list) else str(data["eligible_batch_years"])

    # Update skills if provided
    if "skills" in data:
        JobSkill.query.filter_by(job_id=job.id).delete()
        for s in data["skills"]:
            s_name = s.get("name", "").strip()
            if not s_name: continue
            priority = (s.get("priority") or "Important").capitalize()
            catalog_skill = Skill.query.filter_by(name=s_name).first()
            if not catalog_skill:
                catalog_skill = Skill(name=s_name, category="Technical")
                db.session.add(catalog_skill)
                db.session.flush()
            db.session.add(JobSkill(
                job_id=job.id,
                skill_id=catalog_skill.id,
                priority=priority,
                is_mandatory=(priority in ["Critical", "Important"]),
                min_proficiency=s.get("min_proficiency", "Intermediate")
            ))

    # If job was rejected, reset to Pending Approval
    if job.status == "Rejected":
        job.status = "Pending Approval"
        job.rejection_reason = None

    db.session.commit()

    return api_response(message="Job listing updated successfully.", data={"id": job.id, "status": job.status}, status_code=200)


@industry_bp.route("/jobs", methods=["GET"])
@industry_required
def get_industry_jobs(current_user):
    """
    Lists all job listings created by the logged-in industry expert,
    including moderation status and applicant counts.
    """
    expert = current_user.industry_profile
    if not expert:
        return error_response("Industry profile not found.", 404)

    jobs = Job.query.filter_by(posted_by_expert_id=expert.id).order_by(Job.created_at.desc()).all()

    results = []
    for j in jobs:
        results.append({
            "id": j.id,
            "title": j.title,
            "job_type": j.job_type,
            "location": j.location,
            "ctc": j.ctc,
            "domain": j.domain,
            "status": j.status,
            "rejection_reason": j.rejection_reason,
            "created_at": j.created_at.strftime("%b %d, %Y") if j.created_at else None,
            "deadline": j.deadline.strftime("%b %d, %Y") if j.deadline else "None",
            "skills": [
                {"name": js.skill.name, "priority": js.priority}
                for js in j.required_skills if js.skill
            ],
            "applications_count": len(j.applications)
        })

    return api_response(message="Industry jobs retrieved.", data={"total": len(results), "jobs": results}, status_code=200)


@industry_bp.route("/jobs/<int:job_id>/applications", methods=["GET"])
@industry_required
def get_job_applications(current_user, job_id):
    """
    Retrieves all student applications for a specific job, with candidate profile,
    resume score, calculated match score, and status history.
    """
    expert = current_user.industry_profile
    job = Job.query.get(job_id)
    if not job or job.posted_by_expert_id != expert.id:
        return error_response("Job posting not found or unauthorized.", 404)

    applications = Application.query.filter_by(job_id=job.id).order_by(Application.applied_at.desc()).all()

    candidates = []
    for app in applications:
        student = app.student
        match_info = calculate_job_match(student, job) if student else None
        
        # Primary resume info
        resume = app.resume
        resume_score = None
        if resume and resume.analysis and resume.analysis.overall_score:
            resume_score = float(resume.analysis.overall_score)

        candidates.append({
            "id": app.id,
            "application_id": app.id,
            "student": {
                "id": student.id if student else None,
                "name": f"{student.first_name} {student.last_name}" if student else "Candidate",
                "email": student.user.email if student and student.user else "N/A",
                "roll_number": student.roll_number if student else "N/A",
                "department": student.department if student else "N/A",
                "batch_year": student.batch_year if student else "N/A",
                "cgpa": float(student.cgpa) if student and student.cgpa else None
            },
            "resume": {
                "id": resume.id if resume else None,
                "file_name": resume.file_name if resume else None,
                "score": resume_score
            },
            "status": app.current_status,
            "current_status": app.current_status,
            "applied_at": app.applied_at.strftime("%b %d, %Y %I:%M %p") if app.applied_at else "Recently",
            "match_score": match_info["overall_match"] if match_info else 0,
            "match": {
                "overall_match": match_info["overall_match"] if match_info else 0,
                "skill_match": match_info["skill_match"] if match_info else 0,
                "role_match": match_info["role_match"] if match_info else 0,
                "is_eligible": match_info["eligibility"]["is_eligible"] if match_info else True,
                "matched_skills": match_info["skill_details"]["matched_skills"] if match_info else []
            },
            "status_history": [
                {
                    "status": h.status,
                    "notes": h.notes,
                    "time": h.created_at.strftime("%b %d, %Y %I:%M %p") if h.created_at else None
                }
                for h in app.status_history
            ]
        })

    # Sort by overall match score
    candidates.sort(key=lambda c: c["match"]["overall_match"], reverse=True)

    return api_response(
        message=f"Applications for '{job.title}' retrieved.",
        data={
            "job": {
                "id": job.id,
                "title": job.title,
                "status": job.status
            },
            "total_applicants": len(candidates),
            "allowed_statuses": ALLOWED_STATUSES,
            "applicants": candidates
        },
        status_code=200
    )


@industry_bp.route("/applications/<int:app_id>/status", methods=["PUT"])
@industry_required
def update_application_status(current_user, app_id):
    """
    Transitions candidate application status:
    APPLIED -> UNDER_REVIEW -> SHORTLISTED -> ASSESSMENT -> INTERVIEW -> SELECTED / REJECTED
    Logs transition audit record in ApplicationStatusHistory.
    """
    expert = current_user.industry_profile
    application = Application.query.get(app_id)
    if not application or not application.job or application.job.posted_by_expert_id != expert.id:
        return error_response("Application not found or unauthorized.", 404)

    data = request.get_json() or {}
    new_status = data.get("status", "").strip().upper()
    notes = data.get("notes", "").strip()

    if new_status not in ALLOWED_STATUSES:
        return error_response(f"Invalid status '{new_status}'. Allowed values: {', '.join(ALLOWED_STATUSES)}", 400)

    old_status = application.current_status
    application.current_status = new_status

    # Record status history
    history = ApplicationStatusHistory(
        application_id=application.id,
        status=new_status,
        notes=notes or f"Status updated from {old_status} to {new_status} by recruiter.",
        changed_by_user_id=current_user.id
    )
    db.session.add(history)
    db.session.commit()

    return api_response(
        message=f"Application status updated to {new_status}.",
        data={
            "application_id": application.id,
            "old_status": old_status,
            "status": new_status,
            "new_status": new_status,
            "notes": history.notes,
            "updated_at": history.created_at.strftime("%b %d, %Y %I:%M %p")
        },
        status_code=200
    )


# ============================================================================
# 1. INDUSTRY DASHBOARD & METRICS
# ============================================================================

@industry_bp.route("/dashboard", methods=["GET"])
@industry_required
def get_industry_dashboard(current_user):
    """
    Returns aggregated recruiter analytics:
    - Active & total job counts
    - Total applications & candidate pipeline stage breakdown
    - Upcoming scheduled workshops & active assessments
    - Skill demand analytics compared against student talent supply
    """
    expert = current_user.industry_profile
    if not expert:
        return error_response("Industry profile not found.", 404)

    company = expert.company
    if not company:
        return api_response(
            message="No company profile linked yet.",
            data={
                "company": None,
                "active_jobs_count": 0,
                "pending_jobs_count": 0,
                "total_jobs_count": 0,
                "total_applications_count": 0,
                "shortlisted_count": 0,
                "upcoming_workshops_count": 0,
                "assessments_count": 0,
                "candidate_statistics": {status: 0 for status in ALLOWED_STATUSES},
                "skill_demand": []
            }
        )

    # 1. Jobs breakdown
    all_jobs = Job.query.filter_by(company_id=company.id).all()
    active_jobs = [j for j in all_jobs if j.status in ["Published", "Approved"]]
    pending_jobs = [j for j in all_jobs if j.status == "Pending Approval"]

    # 2. Candidate pipeline breakdown
    job_ids = [j.id for j in all_jobs]
    applications = Application.query.filter(Application.job_id.in_(job_ids)).all() if job_ids else []

    candidate_stats = {s: 0 for s in ALLOWED_STATUSES}
    for app in applications:
        status_key = app.current_status.upper() if app.current_status else "APPLIED"
        if status_key in candidate_stats:
            candidate_stats[status_key] += 1

    shortlisted_count = (
        candidate_stats.get("SHORTLISTED", 0) +
        candidate_stats.get("ASSESSMENT", 0) +
        candidate_stats.get("INTERVIEW", 0) +
        candidate_stats.get("SELECTED", 0)
    )

    # 3. Workshops & Assessments
    now = datetime.now(timezone.utc)
    workshops = Workshop.query.filter_by(company_id=company.id).all()
    upcoming_workshops = []
    for w in workshops:
        if w.start_time:
            st = w.start_time if w.start_time.tzinfo else w.start_time.replace(tzinfo=timezone.utc)
            if st >= now:
                upcoming_workshops.append(w)
    assessments = Assessment.query.filter_by(company_id=company.id, is_active=True).all()

    # 4. Skill Demand Analytics
    skill_demand_map = {}
    for job in all_jobs:
        for js in job.required_skills:
            if not js.skill:
                continue
            name = js.skill.name
            if name not in skill_demand_map:
                skill_demand_map[name] = {
                    "skill_name": name,
                    "demand_count": 0,
                    "critical_count": 0,
                    "important_count": 0,
                    "preferred_count": 0
                }
            skill_demand_map[name]["demand_count"] += 1
            p = (js.priority or "Important").capitalize()
            if p == "Critical":
                skill_demand_map[name]["critical_count"] += 1
            elif p == "Important":
                skill_demand_map[name]["important_count"] += 1
            else:
                skill_demand_map[name]["preferred_count"] += 1

    skill_demand_list = list(skill_demand_map.values())
    skill_demand_list.sort(key=lambda s: s["demand_count"], reverse=True)

    # Measure talent supply in student pool
    for s in skill_demand_list[:10]:
        supply_count = StudentSkill.query.join(Skill).filter(
            db.func.lower(Skill.name) == s["skill_name"].lower()
        ).count()
        s["supply_count"] = supply_count

    return api_response(
        message="Industry dashboard metrics retrieved successfully.",
        data={
            "company": company.to_dict(),
            "active_jobs_count": len(active_jobs),
            "pending_jobs_count": len(pending_jobs),
            "total_jobs_count": len(all_jobs),
            "total_applications_count": len(applications),
            "shortlisted_count": shortlisted_count,
            "upcoming_workshops_count": len(upcoming_workshops),
            "assessments_count": len(assessments),
            "candidate_statistics": candidate_stats,
            "skill_demand": skill_demand_list[:10]
        },
        status_code=200
    )


# ============================================================================
# 2. COMPANY PROFILE & BRANDING MANAGEMENT
# ============================================================================

@industry_bp.route("/company", methods=["GET"])
@industry_required
def get_company_profile(current_user):
    """Retrieves the corporate profile and multimedia content for the recruiter's company."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)
    return api_response(
        message="Company profile retrieved.",
        data={"company": expert.company.to_dict()},
        status_code=200
    )


@industry_bp.route("/company", methods=["PUT"])
@industry_required
def update_company_profile(current_user):
    """
    Updates company name, description, logo, website, industry, domains,
    locations, recruitment process, and company videos/content.
    """
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    company = expert.company
    data = request.get_json() or {}

    if "name" in data and data["name"].strip():
        new_name = data["name"].strip()
        existing = Company.query.filter(Company.name == new_name, Company.id != company.id).first()
        if existing:
            return error_response("A company with this name already exists.", 409)
        company.name = new_name

    if "description" in data:
        company.description = data["description"].strip()
    if "logo_url" in data:
        company.logo_url = data["logo_url"].strip()
    if "website" in data:
        company.website = data["website"].strip()
    if "industry" in data:
        company.industry_type = data["industry"].strip()
    elif "industry_type" in data:
        company.industry_type = data["industry_type"].strip()
    if "domains" in data:
        company.domains = data["domains"].strip()
    if "location" in data:
        company.location = data["location"].strip()
    if "recruitment_process" in data:
        company.recruitment_process = data["recruitment_process"].strip()
    if "videos" in data:
        company.videos_json = json.dumps(data["videos"]) if isinstance(data["videos"], list) else str(data["videos"])

    db.session.commit()
    return api_response(
        message="Company profile updated successfully.",
        data={"company": company.to_dict()},
        status_code=200
    )


# ============================================================================
# 3. TALENT SEARCH & DECISION-SUPPORT MATCHING
# ============================================================================

@industry_bp.route("/talent-search", methods=["GET"])
@industry_required
def talent_search(current_user):
    """
    Advanced candidate discovery with filtering by:
    - Skills (matched against student catalog & extracted resume text)
    - Domain & Role
    - Branch / Department
    - Minimum CGPA
    - Graduation Batch Year
    - Minimum Resume ATS score
    - Minimum Placement Readiness score

    Provides decision-support candidate match score.
    NOTE: Decision-support advisory only; does not make automated hiring decisions.
    """
    skill_filter = request.args.get("skill", "").strip().lower()
    domain_filter = request.args.get("domain", "").strip().lower()
    role_filter = request.args.get("role", "").strip().lower()
    branch_filter = request.args.get("branch", "").strip().lower()
    min_cgpa = request.args.get("min_cgpa", type=float)
    batch_year = request.args.get("batch_year", type=int)
    min_resume_score = request.args.get("min_resume_score", type=float)
    min_readiness = request.args.get("min_readiness", type=float)
    job_id = request.args.get("job_id", type=int)

    reference_job = None
    if job_id:
        reference_job = Job.query.get(job_id)

    query = Student.query.join(User).filter(User.is_active == True)

    if branch_filter:
        query = query.filter(db.func.lower(Student.department).like(f"%{branch_filter}%"))
    if min_cgpa is not None:
        query = query.filter(Student.cgpa >= min_cgpa)
    if batch_year is not None:
        query = query.filter(Student.batch_year == batch_year)

    students = query.all()
    results = []

    for s in students:
        # Student skills from profile
        s_skills = [ss.skill.name for ss in s.student_skills if ss.skill]
        s_skills_lower = [name.lower() for name in s_skills]

        # Primary resume info
        primary_resume = next((r for r in s.resumes if r.is_primary), s.resumes[-1] if s.resumes else None)
        resume_score = 0.0
        parsed_skills = []
        if primary_resume and primary_resume.analysis:
            resume_score = float(primary_resume.analysis.overall_score or 0.0)
            if primary_resume.analysis.parsed_skills_json:
                try:
                    p_raw = json.loads(primary_resume.analysis.parsed_skills_json)
                    for item in p_raw:
                        if isinstance(item, dict) and "name" in item:
                            parsed_skills.append(item["name"].lower())
                        elif isinstance(item, str):
                            parsed_skills.append(item.lower())
                except Exception:
                    pass

        all_candidate_skills = set(s_skills_lower + parsed_skills)

        # Skill filter
        if skill_filter and not any(skill_filter in sk for sk in all_candidate_skills):
            continue

        # Domain & Role filters
        pref = s.preferences
        candidate_domain = (pref.preferred_domain if pref else "") or s.department or ""
        candidate_roles = (pref.preferred_roles if pref else "") or ""

        if domain_filter and domain_filter not in candidate_domain.lower():
            continue
        if role_filter and role_filter not in candidate_roles.lower():
            continue

        # Resume score filter
        if min_resume_score is not None and resume_score < min_resume_score:
            continue

        # Placement Readiness formula
        cgpa_norm = min(100.0, (float(s.cgpa or 0.0) / 10.0) * 100.0)
        skill_norm = min(100.0, len(s_skills) * 15.0)
        placement_readiness = round((0.40 * cgpa_norm) + (0.30 * resume_score) + (0.30 * skill_norm), 1)

        if min_readiness is not None and placement_readiness < min_readiness:
            continue

        # Decision-Support Match Score
        match_info = None
        if reference_job:
            match_info = calculate_job_match(s, reference_job)
            decision_support_score = match_info["overall_match"]
        else:
            decision_support_score = min(100.0, round((placement_readiness * 0.7) + (len(s_skills) * 3), 1))

        results.append({
            "id": s.id,
            "name": f"{s.first_name} {s.last_name}",
            "email": s.user.email if s.user else "N/A",
            "roll_number": s.roll_number,
            "department": s.department,
            "degree": s.degree,
            "batch_year": s.batch_year,
            "cgpa": float(s.cgpa) if s.cgpa else None,
            "skills": [{"name": ss.skill.name, "proficiency": ss.proficiency_level} for ss in s.student_skills if ss.skill],
            "resume": {
                "id": primary_resume.id if primary_resume else None,
                "file_name": primary_resume.file_name if primary_resume else None,
                "score": resume_score
            },
            "placement_readiness": placement_readiness,
            "decision_support_match_score": decision_support_score,
            "match_details": match_info,
            "preferences": {
                "preferred_domain": pref.preferred_domain if pref else None,
                "preferred_roles": pref.preferred_roles if pref else None,
                "job_type": pref.job_type_preference if pref else "Both",
                "locations": pref.preferred_locations if pref else None
            }
        })

    # Sort descending by match score
    results.sort(key=lambda x: x["decision_support_match_score"], reverse=True)

    return api_response(
        message="Talent search candidates retrieved.",
        data={
            "total_candidates": len(results),
            "disclaimer": "This candidate match score is an advisory decision-support metric only and must not automatically make hiring decisions.",
            "candidates": results
        },
        status_code=200
    )


# ============================================================================
# 4. ASSESSMENT CREATION & RESULTS MANAGEMENT
# ============================================================================

@industry_bp.route("/assessments", methods=["POST"])
@industry_required
def create_assessment(current_user):
    """
    Creates a pre-placement assessment with MCQ or technical questions.
    Can be optionally linked to a specific job opening.
    """
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return error_response("Assessment title is required.", 400)

    job_id = data.get("job_id")
    if job_id:
        job = Job.query.filter_by(id=job_id, company_id=expert.company.id).first()
        if not job:
            return error_response("Linked job does not belong to your company.", 400)

    assessment = Assessment(
        title=title,
        description=data.get("description", "").strip(),
        company_id=expert.company.id,
        job_id=job_id,
        duration_minutes=int(data.get("duration_minutes", 60)),
        passing_score=float(data.get("passing_score", 40.0)),
        is_active=True
    )
    db.session.add(assessment)
    db.session.flush()

    questions_data = data.get("questions", [])
    for q in questions_data:
        q_text = q.get("question_text", "").strip()
        if not q_text:
            continue
        correct = q.get("correct_answer", "").strip()
        options = q.get("options", [])
        question = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text=q_text,
            question_type=q.get("question_type", "MCQ"),
            options_json=json.dumps(options) if isinstance(options, list) else str(options),
            correct_answer=correct,
            marks=float(q.get("marks", 1.0))
        )
        db.session.add(question)

    db.session.commit()

    return api_response(
        message="Assessment created successfully.",
        data={"assessment": assessment.to_dict(include_questions=True)},
        status_code=201
    )


@industry_bp.route("/assessments", methods=["GET"])
@industry_required
def list_assessments(current_user):
    """Lists all assessments belonging to the recruiter's company."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    assessments = Assessment.query.filter_by(company_id=expert.company.id).order_by(Assessment.created_at.desc()).all()
    return api_response(
        message="Assessments retrieved successfully.",
        data={"assessments": [a.to_dict(include_questions=True) for a in assessments]},
        status_code=200
    )


@industry_bp.route("/assessments/<int:assessment_id>/results", methods=["GET"])
@industry_required
def get_assessment_results(current_user, assessment_id):
    """Retrieves all candidate attempts, scores, and pass/fail results for an assessment."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    assessment = Assessment.query.filter_by(id=assessment_id, company_id=expert.company.id).first()
    if not assessment:
        return error_response("Assessment not found or unauthorized.", 404)

    attempts = AssessmentAttempt.query.filter_by(assessment_id=assessment.id).order_by(AssessmentAttempt.created_at.desc()).all()
    return api_response(
        message=f"Results for '{assessment.title}' retrieved.",
        data={
            "assessment": assessment.to_dict(),
            "total_attempts": len(attempts),
            "passed_count": len([att for att in attempts if att.passed]),
            "attempts": [att.to_dict() for att in attempts]
        },
        status_code=200
    )


# ============================================================================
# 5. STRUCTURED CANDIDATE FEEDBACK & EVALUATION
# ============================================================================

@industry_bp.route("/applications/<int:app_id>/feedback", methods=["POST"])
@industry_required
def submit_candidate_feedback(current_user, app_id):
    """
    Submits structured interviewer feedback:
    - Technical skills rating (1-5)
    - Problem solving rating (1-5)
    - Communication rating (1-5)
    - Hiring recommendation (Strong Hire, Hire, Hold, Reject)
    - Constructive comments
    - Privacy control: is_visible_to_student (True = shared with candidate, False = internal)
    """
    expert = current_user.industry_profile
    application = Application.query.get(app_id)
    if not application:
        return error_response("Application not found.", 404)

    if application.job.company_id != expert.company_id:
        return error_response("Unauthorized to provide feedback for this application.", 403)

    data = request.get_json() or {}
    comments = data.get("comments", "").strip()
    if not comments:
        return error_response("Feedback comments are required.", 400)

    tech_rating = data.get("technical_rating")
    problem_rating = data.get("problem_solving_rating")
    comm_rating = data.get("communication_rating")
    overall_rating = data.get("rating")
    if overall_rating is None and all(r is not None for r in [tech_rating, problem_rating, comm_rating]):
        overall_rating = round((tech_rating + problem_rating + comm_rating) / 3)

    feedback = Feedback(
        application_id=application.id,
        given_by_user_id=current_user.id,
        target_student_id=application.student_id,
        rating=overall_rating,
        technical_rating=tech_rating,
        problem_solving_rating=problem_rating,
        communication_rating=comm_rating,
        recommendation=data.get("recommendation", "Hold"),
        is_visible_to_student=bool(data.get("is_visible_to_student", False)),
        comments=comments,
        feedback_type=data.get("feedback_type", "Interview")
    )
    db.session.add(feedback)
    db.session.commit()

    return api_response(
        message="Candidate evaluation feedback recorded successfully.",
        data={"feedback": feedback.to_dict()},
        status_code=201
    )


@industry_bp.route("/applications/<int:app_id>/feedback", methods=["GET"])
@industry_required
def get_candidate_feedback(current_user, app_id):
    """Retrieves all feedback entries recorded for an application."""
    expert = current_user.industry_profile
    application = Application.query.get(app_id)
    if not application:
        return error_response("Application not found.", 404)

    if application.job.company_id != expert.company_id:
        return error_response("Unauthorized to view feedback for this application.", 403)

    feedbacks = Feedback.query.filter_by(application_id=application.id).order_by(Feedback.created_at.desc()).all()
    return api_response(
        message="Application feedback records retrieved.",
        data={"feedbacks": [f.to_dict() for f in feedbacks]},
        status_code=200
    )


# ============================================================================
# 6. WORKSHOPS & WEBINARS MANAGEMENT
# ============================================================================

@industry_bp.route("/workshops", methods=["POST"])
@industry_required
def create_workshop(current_user):
    """Schedules a technical webinar, masterclass, or campus workshop."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return error_response("Workshop title is required.", 400)

    start_str = data.get("start_time")
    end_str = data.get("end_time")
    if not start_str or not end_str:
        return error_response("Start time and end time are required.", 400)

    try:
        start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    except ValueError:
        return error_response("Invalid ISO format for start_time or end_time.", 400)

    workshop = Workshop(
        title=title,
        description=data.get("description", "").strip(),
        instructor_id=expert.id,
        company_id=expert.company.id,
        start_time=start_time,
        end_time=end_time,
        venue_or_link=data.get("venue_or_link", "Virtual Session"),
        max_capacity=int(data.get("max_capacity", 100))
    )
    db.session.add(workshop)
    db.session.commit()

    return api_response(
        message="Workshop scheduled successfully.",
        data={
            "workshop": {
                "id": workshop.id,
                "title": workshop.title,
                "description": workshop.description,
                "start_time": workshop.start_time.isoformat(),
                "end_time": workshop.end_time.isoformat(),
                "venue_or_link": workshop.venue_or_link,
                "max_capacity": workshop.max_capacity,
                "instructor": f"{expert.first_name} {expert.last_name}",
                "company": expert.company.name
            }
        },
        status_code=201
    )


@industry_bp.route("/workshops", methods=["GET"])
@industry_required
def list_workshops(current_user):
    """Lists all workshops organized by the recruiter's company."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    workshops = Workshop.query.filter_by(company_id=expert.company.id).order_by(Workshop.start_time.desc()).all()
    results = []
    for w in workshops:
        results.append({
            "id": w.id,
            "title": w.title,
            "description": w.description,
            "start_time": w.start_time.isoformat() if w.start_time else None,
            "end_time": w.end_time.isoformat() if w.end_time else None,
            "venue_or_link": w.venue_or_link,
            "max_capacity": w.max_capacity,
            "registered_count": len(w.registrations),
            "instructor": f"{w.instructor.first_name} {w.instructor.last_name}" if w.instructor else "Lead Instructor"
        })

    return api_response(
        message="Workshops retrieved successfully.",
        data={"workshops": results},
        status_code=200
    )


@industry_bp.route("/workshops/<int:workshop_id>/attendees", methods=["GET"])
@industry_required
def get_workshop_attendees(current_user, workshop_id):
    """Lists all students registered for a specific workshop."""
    expert = current_user.industry_profile
    if not expert or not expert.company:
        return error_response("Company profile not found.", 404)

    workshop = Workshop.query.filter_by(id=workshop_id, company_id=expert.company.id).first()
    if not workshop:
        return error_response("Workshop not found or unauthorized.", 404)

    attendees = []
    for reg in workshop.registrations:
        s = reg.student
        attendees.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}",
            "email": s.user.email if s.user else "N/A",
            "roll_number": s.roll_number,
            "department": s.department,
            "attendance_status": reg.attendance_status,
            "registered_at": reg.created_at.isoformat() if reg.created_at else None
        })

    return api_response(
        message=f"Attendees for '{workshop.title}' retrieved.",
        data={
            "workshop_id": workshop.id,
            "title": workshop.title,
            "total_registered": len(attendees),
            "attendees": attendees
        },
        status_code=200
    )

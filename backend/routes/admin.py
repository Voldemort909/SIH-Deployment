"""
Administrator / College Placement Cell Management Routes.
Guarded strictly by @admin_required.

Provides full capabilities for:
1. Executive Placement Dashboard & KPI Analytics (Department/Company stats, salary metrics)
2. Student Directory & At-Risk Candidate Detection Engine with Intervention Tracking
3. Industry Expert Verification Queue (PENDING -> APPROVED / REJECTED)
4. Corporate Partner & Company Management
5. Job Posting Moderation & Compliance Pipeline
6. End-to-End Placement Drive Workflow Management (Eligibility, Registration, Stages, Offer)
7. Campus Workshops Monitoring
8. Alumni Directory & Mentorship Network
9. Broadcast Announcements & Automated Notification Dispatcher
10. Placement Summary Reports & CSV Exports
"""
import io
import csv
import json
from datetime import datetime, timezone
from flask import Blueprint, request, Response
from sqlalchemy import func, distinct, or_, and_

from backend.extensions import db
from backend.models.user import User, Student, IndustryExpert, Admin
from backend.models.company import Company
from backend.models.job import Job
from backend.models.skill import Skill, StudentSkill, JobSkill
from backend.models.application import Application, Feedback
from backend.models.assessment import Assessment, AssessmentAttempt
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.resume import Resume, ResumeAnalysis
from backend.models.placement import (
    PlacementRecord,
    PlacementDrive,
    PlacementDriveStudent,
    Alumni,
    Announcement,
    StudentIntervention,
)
from backend.models.notification import Notification
from backend.services.notification_service import NotificationService
from backend.utils.auth import admin_required
from backend.utils.response import api_response, error_response

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# =====================================================================
# 1. EXECUTIVE DASHBOARD & PLACEMENT ANALYTICS
# =====================================================================

@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def get_admin_dashboard(current_user):
    """
    Aggregates comprehensive campus-wide placement metrics:
    - High-level KPIs: Total students, companies, recruiters, active jobs, placement drives.
    - Placement outcomes: Placed students count, placement rate %, average CTC, highest CTC.
    - Department-wise breakdown & company-wise recruitment distribution.
    - At-risk students count requiring placement cell assistance.
    """
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_experts = IndustryExpert.query.count()
    pending_experts = IndustryExpert.query.filter_by(status="PENDING").count()
    active_jobs = Job.query.filter_by(status="Published").count()
    pending_jobs = Job.query.filter_by(status="Pending Approval").count()
    total_drives = PlacementDrive.query.count()
    ongoing_drives = PlacementDrive.query.filter(PlacementDrive.status.in_(["Scheduled", "Ongoing"])).count()

    # Placed students calculation:
    # 1. Official records in placement_records with accepted/pending status
    # 2. Or Applications marked as 'SELECTED'
    placed_student_ids = set([
        r[0] for r in db.session.query(PlacementRecord.student_id).filter(
            PlacementRecord.acceptance_status != "Declined"
        ).distinct().all()
    ])

    selected_app_student_ids = set([
        r[0] for r in db.session.query(Application.student_id).filter(
            Application.current_status == "SELECTED"
        ).distinct().all()
    ])

    drive_offered_student_ids = set([
        r[0] for r in db.session.query(PlacementDriveStudent.student_id).filter(
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).distinct().all()
    ])

    all_placed_ids = placed_student_ids.union(selected_app_student_ids).union(drive_offered_student_ids)
    students_placed_count = len(all_placed_ids)
    placement_rate = round((students_placed_count / total_students * 100), 1) if total_students > 0 else 0.0

    # CTC calculations from placement records
    ctc_records = db.session.query(PlacementRecord.package_ctc).filter(
        PlacementRecord.package_ctc.isnot(None),
        PlacementRecord.acceptance_status != "Declined"
    ).all()

    # Also harvest drive offered CTCs
    drive_ctcs = db.session.query(PlacementDriveStudent.offered_ctc).filter(
        PlacementDriveStudent.offered_ctc.isnot(None),
        PlacementDriveStudent.stage.in_(["Offered", "Selected"])
    ).all()

    all_ctcs = [float(r[0]) for r in ctc_records if r[0] is not None] + [float(r[0]) for r in drive_ctcs if r[0] is not None]

    if all_ctcs:
        avg_ctc = round(sum(all_ctcs) / len(all_ctcs), 2)
        highest_ctc = round(max(all_ctcs), 2)
    else:
        avg_ctc = 0.0
        highest_ctc = 0.0

    # Department-wise placement breakdown
    departments = db.session.query(Student.department).distinct().all()
    department_stats = []

    for (dept,) in departments:
        if not dept:
            continue
        dept_total = Student.query.filter_by(department=dept).count()
        dept_students = db.session.query(Student.id).filter_by(department=dept).all()
        dept_student_ids = set(s[0] for s in dept_students)
        dept_placed = len(dept_student_ids.intersection(all_placed_ids))
        dept_rate = round((dept_placed / dept_total * 100), 1) if dept_total > 0 else 0.0

        # Department CTC
        dept_ctc_vals = [
            float(r.package_ctc) for r in PlacementRecord.query.join(Student).filter(
                Student.department == dept,
                PlacementRecord.package_ctc.isnot(None),
                PlacementRecord.acceptance_status != "Declined"
            ).all()
        ]
        dept_avg_ctc = round(sum(dept_ctc_vals) / len(dept_ctc_vals), 2) if dept_ctc_vals else 0.0

        department_stats.append({
            "department": dept,
            "total_students": dept_total,
            "placed_students": dept_placed,
            "unplaced_students": dept_total - dept_placed,
            "placement_rate": dept_rate,
            "avg_ctc": dept_avg_ctc
        })

    # Sort departments by total students descending
    department_stats.sort(key=lambda x: x["total_students"], reverse=True)

    # Company-wise placement leaderboard
    companies = Company.query.all()
    company_stats = []
    for c in companies:
        direct_hires = PlacementRecord.query.filter_by(company_id=c.id).filter(
            PlacementRecord.acceptance_status != "Declined"
        ).count()
        app_hires = Application.query.join(Job).filter(
            Job.company_id == c.id,
            Application.current_status == "SELECTED"
        ).count()
        drive_hires = PlacementDriveStudent.query.join(PlacementDrive).filter(
            PlacementDrive.company_id == c.id,
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).count()

        total_hires = max(direct_hires, app_hires + drive_hires)
        if total_hires > 0 or c.placement_drives or c.jobs:
            company_stats.append({
                "id": c.id,
                "name": c.name,
                "industry": c.industry_type,
                "hires_count": total_hires,
                "active_jobs_count": len([j for j in c.jobs if j.status == "Published"]),
                "drives_count": len(c.placement_drives)
            })

    company_stats.sort(key=lambda x: x["hires_count"], reverse=True)

    # At-risk students count
    at_risk_list = compute_at_risk_students()
    at_risk_count = len(at_risk_list)

    return api_response(
        message="Administrator placement dashboard metrics retrieved successfully.",
        data={
            "summary_kpis": {
                "total_students": total_students,
                "total_companies": total_companies,
                "total_industry_experts": total_experts,
                "pending_experts_verification": pending_experts,
                "active_jobs": active_jobs,
                "pending_jobs_moderation": pending_jobs,
                "total_drives": total_drives,
                "ongoing_drives": ongoing_drives,
                "students_placed": students_placed_count,
                "placement_rate": placement_rate,
                "average_ctc": avg_ctc,
                "highest_ctc": highest_ctc,
                "students_requiring_assistance": at_risk_count
            },
            "department_wise": department_stats,
            "company_wise": company_stats[:10],
            "at_risk_preview": at_risk_list[:5]
        },
        status_code=200
    )


# =====================================================================
# 2. STUDENT DIRECTORY & AT-RISK IDENTIFICATION ENGINE
# =====================================================================

def evaluate_student_risk(student):
    """
    Evaluates risk indicators for an individual student:
    - Low resume score (< 50% or no resume uploaded)
    - Major skill gaps (< 2 skills logged)
    - Very few applications (<= 1 application)
    - Repeated rejections (>= 2 rejections without any active offer)
    - Low assessment performance (average score < 50%)
    - Academic risk (CGPA < 6.0 or active backlogs > 0)
    """
    indicators = []
    risk_points = 0

    # 1. Placement Check (if placed, student is not at risk)
    is_placed = (
        PlacementRecord.query.filter_by(student_id=student.id).filter(PlacementRecord.acceptance_status != "Declined").first()
        or Application.query.filter_by(student_id=student.id, current_status="SELECTED").first()
        or PlacementDriveStudent.query.filter_by(student_id=student.id).filter(PlacementDriveStudent.stage.in_(["Offered", "Selected"])).first()
    )
    if is_placed:
        return None

    # 2. Resume ATS Score
    latest_resume = Resume.query.filter_by(student_id=student.id).order_by(Resume.created_at.desc()).first()
    if not latest_resume:
        indicators.append("No resume uploaded to system")
        risk_points += 2
        resume_score = 0
    else:
        analysis = latest_resume.analysis
        resume_score = float(analysis.ats_score) if (analysis and analysis.ats_score is not None) else 0
        if resume_score < 50:
            indicators.append(f"Low resume ATS score ({resume_score}%)")
            risk_points += 2

    # 3. Skills Check
    skills_count = len(student.student_skills)
    if skills_count == 0:
        indicators.append("No technical skills registered on profile")
        risk_points += 2
    elif skills_count < 2:
        indicators.append("Severe skill gap: less than 2 skills logged")
        risk_points += 1

    # 4. Applications and Rejection History
    apps = student.applications
    total_apps = len(apps)
    rejections = len([a for a in apps if a.current_status == "REJECTED"])

    if total_apps <= 1:
        indicators.append(f"Very few job applications submitted ({total_apps})")
        risk_points += 1

    if rejections >= 2:
        indicators.append(f"Repeated rejections ({rejections} rejections without offers)")
        risk_points += 2

    # 5. Assessment Attempts
    attempts = student.assessment_attempts
    if attempts:
        avg_score = sum([float(a.score) for a in attempts if a.score is not None]) / len(attempts)
        if avg_score < 50.0:
            indicators.append(f"Low test performance: avg {round(avg_score, 1)}% in screening assessments")
            risk_points += 2

    # 6. Academic Standing
    if student.cgpa and float(student.cgpa) < 6.0:
        indicators.append(f"Low CGPA: {float(student.cgpa)}/10.0")
        risk_points += 1

    if student.backlogs and student.backlogs > 0:
        indicators.append(f"Active academic backlogs ({student.backlogs})")
        risk_points += 2

    if risk_points >= 2 or len(indicators) >= 2:
        severity = "HIGH" if risk_points >= 5 else ("MEDIUM" if risk_points >= 3 else "LOW")
        return {
            "student_id": student.id,
            "roll_number": student.roll_number,
            "name": f"{student.first_name} {student.last_name}",
            "email": student.user.email if student.user else "N/A",
            "department": student.department,
            "batch_year": student.batch_year,
            "cgpa": float(student.cgpa) if student.cgpa else None,
            "backlogs": student.backlogs,
            "resume_score": resume_score if 'resume_score' in locals() else 0,
            "total_applications": total_apps,
            "rejections": rejections,
            "skills_count": skills_count,
            "severity": severity,
            "risk_score": risk_points,
            "indicators": indicators,
            "interventions_count": len(student.interventions),
            "latest_intervention": {
                "type": student.interventions[-1].intervention_type,
                "status": student.interventions[-1].status,
                "date": student.interventions[-1].created_at.strftime("%b %d, %Y")
            } if student.interventions else None
        }

    return None


def compute_at_risk_students(department=None, batch_year=None):
    """Evaluates all unplaced students to find candidates requiring placement cell assistance."""
    query = Student.query
    if department:
        query = query.filter_by(department=department)
    if batch_year:
        query = query.filter_by(batch_year=batch_year)

    students = query.all()
    results = []
    for s in students:
        eval_res = evaluate_student_risk(s)
        if eval_res:
            results.append(eval_res)

    results.sort(key=lambda x: (x["risk_score"], x["severity"] == "HIGH"), reverse=True)
    return results


@admin_bp.route("/students", methods=["GET"])
@admin_required
def list_students(current_user):
    """
    Filterable student directory with academic, skill, application, and placement status information.
    """
    dept = request.args.get("department")
    batch = request.args.get("batch_year", type=int)
    placed_filter = request.args.get("placement_status")  # 'placed', 'unplaced'
    search = request.args.get("search", "").strip().lower()

    query = Student.query
    if dept:
        query = query.filter_by(department=dept)
    if batch:
        query = query.filter_by(batch_year=batch)

    students = query.all()
    results = []

    for s in students:
        # Check search match
        full_name = f"{s.first_name} {s.last_name}".lower()
        if search and (search not in full_name and search not in s.roll_number.lower() and search not in (s.user.email.lower() if s.user else "")):
            continue

        # Placement status check
        placement = PlacementRecord.query.filter_by(student_id=s.id).filter(
            PlacementRecord.acceptance_status != "Declined"
        ).first()

        drive_offer = PlacementDriveStudent.query.filter_by(student_id=s.id).filter(
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).first()

        app_selected = Application.query.filter_by(student_id=s.id, current_status="SELECTED").first()

        is_placed = bool(placement or drive_offer or app_selected)
        if placed_filter == "placed" and not is_placed:
            continue
        if placed_filter == "unplaced" and is_placed:
            continue

        # Company and CTC if placed
        placed_company = None
        placed_ctc = None
        if placement:
            placed_company = placement.company.name if placement.company else "Campus Recruiter"
            placed_ctc = f"₹{float(placement.package_ctc)} LPA"
        elif drive_offer:
            placed_company = drive_offer.drive.company.name if (drive_offer.drive and drive_offer.drive.company) else "Drive Recruiter"
            placed_ctc = f"₹{float(drive_offer.offered_ctc)} LPA" if drive_offer.offered_ctc else (drive_offer.drive.package_ctc or "Selected")
        elif app_selected:
            placed_company = app_selected.job.company.name if (app_selected.job and app_selected.job.company) else "Company"
            placed_ctc = app_selected.job.ctc or "Selected"

        # Resume score
        latest_res = Resume.query.filter_by(student_id=s.id).order_by(Resume.created_at.desc()).first()
        ats_score = float(latest_res.analysis.ats_score) if (latest_res and latest_res.analysis and latest_res.analysis.ats_score is not None) else None

        # Risk assessment
        risk = evaluate_student_risk(s)

        results.append({
            "id": s.id,
            "roll_number": s.roll_number,
            "name": f"{s.first_name} {s.last_name}",
            "email": s.user.email if s.user else "",
            "department": s.department,
            "degree": s.degree,
            "batch_year": s.batch_year,
            "cgpa": float(s.cgpa) if s.cgpa else None,
            "backlogs": s.backlogs,
            "skills_count": len(s.student_skills),
            "applications_count": len(s.applications),
            "is_placed": is_placed,
            "placed_company": placed_company,
            "placed_ctc": placed_ctc,
            "resume_ats_score": ats_score,
            "is_at_risk": bool(risk),
            "risk_severity": risk["severity"] if risk else None,
            "risk_indicators": risk["indicators"] if risk else []
        })

    return api_response(
        message="Students retrieved successfully.",
        data={"total": len(results), "students": results},
        status_code=200
    )


@admin_bp.route("/students/at-risk", methods=["GET"])
@admin_required
def get_at_risk_students(current_user):
    """
    Returns list of students flagged as at-risk with explainable indicators and intervention histories.
    """
    dept = request.args.get("department")
    batch = request.args.get("batch_year", type=int)

    at_risk = compute_at_risk_students(department=dept, batch_year=batch)
    return api_response(
        message="At-risk students evaluated successfully.",
        data={"total": len(at_risk), "at_risk_students": at_risk},
        status_code=200
    )


@admin_bp.route("/students/<int:student_id>/interventions", methods=["POST"])
@admin_required
def create_intervention(current_user, student_id):
    """
    Records a proactive placement cell intervention for an at-risk student.
    Dispatches an in-app notification to the student with counseling action steps.
    """
    student = Student.query.get(student_id)
    if not student:
        return error_response("Student not found.", 404)

    data = request.get_json() or {}
    intervention_type = data.get("intervention_type", "Counseling Session")
    action_plan = data.get("action_plan", "").strip()
    notes = data.get("notes", "").strip()
    status = data.get("status", "OPEN").upper()

    # Harvest evaluated indicators
    eval_res = evaluate_student_risk(student)
    risk_indicators_str = ", ".join(eval_res["indicators"]) if eval_res else "Manual Placement Flag"

    intervention = StudentIntervention(
        student_id=student.id,
        admin_id=current_user.id,
        risk_indicators=risk_indicators_str,
        intervention_type=intervention_type,
        action_plan=action_plan,
        notes=notes,
        status=status
    )
    db.session.add(intervention)

    # Notify student
    if student.user:
        notif = Notification(
            user_id=student.user.id,
            title=f"Placement Cell Support: {intervention_type}",
            message=f"The Placement Cell has scheduled a {intervention_type} for you. Action Plan: {action_plan or 'Please visit the Placement Cell office.'}",
            type="Placement",
            link="/pages/student/dashboard.html"
        )
        db.session.add(notif)

    db.session.commit()

    return api_response(
        message="Student intervention recorded and student notified successfully.",
        data={
            "id": intervention.id,
            "student_id": student.id,
            "intervention_type": intervention.intervention_type,
            "status": intervention.status,
            "created_at": intervention.created_at.strftime("%b %d, %Y")
        },
        status_code=201
    )


@admin_bp.route("/students/<int:student_id>/interventions", methods=["GET"])
@admin_required
def get_student_interventions(current_user, student_id):
    """Retrieves all past and active interventions recorded for a student."""
    student = Student.query.get(student_id)
    if not student:
        return error_response("Student not found.", 404)

    interventions = StudentIntervention.query.filter_by(student_id=student_id).order_by(
        StudentIntervention.created_at.desc()
    ).all()

    results = []
    for itv in interventions:
        results.append({
            "id": itv.id,
            "intervention_type": itv.intervention_type,
            "risk_indicators": itv.risk_indicators,
            "action_plan": itv.action_plan,
            "notes": itv.notes,
            "status": itv.status,
            "admin_name": f"{itv.assigned_admin.admin_profile.first_name} {itv.assigned_admin.admin_profile.last_name}" if (itv.assigned_admin and itv.assigned_admin.admin_profile) else (itv.assigned_admin.email if itv.assigned_admin else "Placement Cell"),
            "created_at": itv.created_at.strftime("%b %d, %Y %I:%M %p"),
            "updated_at": itv.updated_at.strftime("%b %d, %Y %I:%M %p") if itv.updated_at else None
        })

    return api_response(
        message="Interventions retrieved successfully.",
        data={"interventions": results},
        status_code=200
    )


@admin_bp.route("/interventions/<int:intervention_id>/status", methods=["PUT"])
@admin_required
def update_intervention_status(current_user, intervention_id):
    """Updates the status of an ongoing student intervention (OPEN, IN_PROGRESS, RESOLVED)."""
    intervention = StudentIntervention.query.get(intervention_id)
    if not intervention:
        return error_response("Intervention record not found.", 404)

    data = request.get_json() or {}
    new_status = data.get("status", "").upper()
    if new_status not in ["OPEN", "IN_PROGRESS", "RESOLVED"]:
        return error_response("Invalid status. Allowed values: OPEN, IN_PROGRESS, RESOLVED", 400)

    intervention.status = new_status
    if "notes" in data:
        intervention.notes = data["notes"]
    if "action_plan" in data:
        intervention.action_plan = data["action_plan"]

    db.session.commit()
    return api_response(
        message=f"Intervention status updated to {new_status}.",
        data={"id": intervention.id, "status": intervention.status},
        status_code=200
    )


# =====================================================================
# 3. INDUSTRY EXPERT VERIFICATION & RECRUITER MANAGEMENT
# =====================================================================

@admin_bp.route("/experts", methods=["GET"])
@admin_required
def list_industry_experts(current_user):
    """
    Lists all registered Industry Experts and Recruiters with status filtering (PENDING, APPROVED, REJECTED).
    """
    status_filter = request.args.get("status")
    query = IndustryExpert.query
    if status_filter:
        query = query.filter_by(status=status_filter.upper())

    experts = query.order_by(IndustryExpert.created_at.desc()).all()
    results = []

    for exp in experts:
        results.append({
            "id": exp.id,
            "user_id": exp.user_id,
            "email": exp.user.email if exp.user else "",
            "name": f"{exp.first_name} {exp.last_name}",
            "designation": exp.designation,
            "experience_years": exp.experience_years,
            "linkedin_url": exp.linkedin_url,
            "status": exp.status,
            "company": {
                "id": exp.company.id if exp.company else None,
                "name": exp.company.name if exp.company else "No Company Linked",
                "industry": exp.company.industry_type if exp.company else None,
                "website": exp.company.website if exp.company else None
            },
            "posted_jobs_count": len(exp.posted_jobs),
            "workshops_count": len(exp.workshops),
            "created_at": exp.created_at.strftime("%b %d, %Y %I:%M %p") if exp.created_at else None
        })

    return api_response(
        message="Industry experts retrieved successfully.",
        data={"total": len(results), "experts": results},
        status_code=200
    )


@admin_bp.route("/experts/<int:expert_id>/verify", methods=["PUT"])
@admin_required
def verify_industry_expert(current_user, expert_id):
    """
    Verifies or rejects an industry expert / recruiter registration.
    Flow: PENDING -> Admin review -> APPROVED / REJECTED.
    """
    expert = IndustryExpert.query.get(expert_id)
    if not expert:
        return error_response("Industry expert not found.", 404)

    data = request.get_json() or {}
    action = data.get("action", "").upper()
    notes = data.get("notes", "").strip()

    if action not in ["APPROVE", "REJECT"]:
        return error_response("Invalid action. Must be 'APPROVE' or 'REJECT'.", 400)

    if action == "APPROVE":
        expert.status = "APPROVED"
        notif_msg = "Congratulations! Your industry expert recruiter account has been approved by the Placement Cell. You can now post campus jobs, screening assessments, and schedule technical workshops."
        success_msg = f"Industry expert '{expert.first_name} {expert.last_name}' has been APPROVED."
    else:
        expert.status = "REJECTED"
        notif_msg = f"Your industry expert registration was not approved by the Placement Cell. Feedback: {notes or 'Verification criteria not met.'}"
        success_msg = f"Industry expert '{expert.first_name} {expert.last_name}' has been REJECTED."

    # Dispatch notification to expert user
    if expert.user:
        notif = Notification(
            user_id=expert.user.id,
            title="Account Verification Status Update",
            message=notif_msg,
            type="General",
            link="/pages/recruiter/jobs.html"
        )
        db.session.add(notif)

    db.session.commit()

    return api_response(
        message=success_msg,
        data={
            "id": expert.id,
            "name": f"{expert.first_name} {expert.last_name}",
            "status": expert.status
        },
        status_code=200
    )


# =====================================================================
# 4. COMPANY MANAGEMENT
# =====================================================================

@admin_bp.route("/companies", methods=["GET"])
@admin_required
def list_companies(current_user):
    """Lists all registered recruiting companies with linked drive and job counts."""
    companies = Company.query.order_by(Company.name.asc()).all()
    results = []

    for c in companies:
        results.append({
            "id": c.id,
            "name": c.name,
            "website": c.website,
            "industry_type": c.industry_type,
            "domains": c.domains,
            "location": c.location,
            "locations": c.location,
            "description": c.description,
            "recruitment_process": c.recruitment_process,
            "total_jobs": len(c.jobs),
            "active_jobs": len([j for j in c.jobs if j.status == "Published"]),
            "total_drives": len(c.placement_drives),
            "experts_count": len(c.experts),
            "created_at": c.created_at.strftime("%b %d, %Y") if c.created_at else None
        })

    return api_response(
        message="Companies retrieved successfully.",
        data={"total": len(results), "companies": results},
        status_code=200
    )


@admin_bp.route("/companies", methods=["POST"])
@admin_required
def create_company(current_user):
    """Adds a new corporate recruiting partner to the platform."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return error_response("Company name is required.", 400)

    existing = Company.query.filter(func.lower(Company.name) == func.lower(name)).first()
    if existing:
        return error_response(f"Company '{name}' is already registered.", 409)

    company = Company(
        name=name,
        website=data.get("website", "").strip(),
        industry_type=data.get("industry_type", "Technology").strip(),
        domains=data.get("domains", "").strip(),
        location=(data.get("location") or data.get("locations", "")).strip(),
        description=data.get("description", "").strip(),
        recruitment_process=data.get("recruitment_process", "").strip()
    )
    db.session.add(company)
    db.session.commit()

    return api_response(
        message=f"Company '{company.name}' added successfully.",
        data={"id": company.id, "name": company.name},
        status_code=201
    )


@admin_bp.route("/companies/<int:company_id>", methods=["PUT"])
@admin_required
def update_company(current_user, company_id):
    """Updates company profile and branding details."""
    company = Company.query.get(company_id)
    if not company:
        return error_response("Company not found.", 404)

    data = request.get_json() or {}
    for field in ["name", "website", "industry_type", "domains", "description", "recruitment_process"]:
        if field in data:
            setattr(company, field, data[field].strip())
    if "location" in data or "locations" in data:
        company.location = (data.get("location") or data.get("locations", "")).strip()

    db.session.commit()
    return api_response(
        message=f"Company '{company.name}' updated successfully.",
        data={"id": company.id, "name": company.name},
        status_code=200
    )


# =====================================================================
# 5. JOB MODERATION & COMPLIANCE PIPELINE
# =====================================================================

@admin_bp.route("/jobs", methods=["GET"])
@admin_required
def list_all_jobs(current_user):
    """Lists all campus jobs with optional status filtering ('Pending Approval', 'Published', 'Rejected')."""
    status_filter = request.args.get("status")
    query = Job.query
    if status_filter and status_filter.lower() != "all":
        query = query.filter_by(status=status_filter)

    jobs = query.order_by(Job.created_at.desc()).all()
    results = []

    for j in jobs:
        results.append({
            "id": j.id,
            "title": j.title,
            "company": {
                "id": j.company.id if j.company else None,
                "name": j.company.name if j.company else "Unknown"
            },
            "job_type": j.job_type,
            "location": j.location,
            "domain": j.domain,
            "ctc": j.ctc,
            "min_cgpa": float(j.min_cgpa) if j.min_cgpa else 0.0,
            "eligible_branches": j.eligible_branches,
            "eligible_batch_years": j.eligible_batch_years,
            "deadline": j.deadline.strftime("%b %d, %Y") if j.deadline else "None",
            "status": j.status,
            "rejection_reason": j.rejection_reason,
            "applications_count": len(j.applications),
            "created_at": j.created_at.strftime("%b %d, %Y") if j.created_at else None
        })

    return api_response(
        message="Jobs retrieved successfully.",
        data={"total": len(results), "jobs": results},
        status_code=200
    )


@admin_bp.route("/jobs/pending", methods=["GET"])
@admin_required
def get_pending_jobs(current_user):
    """Lists all job openings awaiting administrator moderation and approval."""
    pending_jobs = Job.query.filter_by(status="Pending Approval").order_by(Job.created_at.desc()).all()

    results = []
    for j in pending_jobs:
        results.append({
            "id": j.id,
            "title": j.title,
            "description": j.description,
            "company": {
                "id": j.company.id if j.company else None,
                "name": j.company.name if j.company else "Unknown Company"
            },
            "posted_by": {
                "name": f"{j.posted_by.first_name} {j.posted_by.last_name}" if j.posted_by else "Industry Recruiter",
                "designation": j.posted_by.designation if j.posted_by else None
            },
            "job_type": j.job_type,
            "location": j.location,
            "domain": j.domain,
            "ctc": j.ctc,
            "min_cgpa": float(j.min_cgpa) if j.min_cgpa else 0.0,
            "eligible_branches": [b.strip() for b in (j.eligible_branches or "").split(",") if b.strip()],
            "eligible_batch_years": [b.strip() for b in (j.eligible_batch_years or "").split(",") if b.strip()],
            "deadline": j.deadline.strftime("%b %d, %Y") if j.deadline else "None",
            "created_at": j.created_at.strftime("%b %d, %Y %I:%M %p") if j.created_at else None,
            "status": j.status,
            "skills": [
                {
                    "name": js.skill.name,
                    "priority": js.priority,
                    "min_proficiency": js.min_proficiency
                }
                for js in j.required_skills if js.skill
            ]
        })

    return api_response(
        message="Pending moderation jobs retrieved successfully.",
        data={
            "total_pending": len(results),
            "jobs": results
        },
        status_code=200
    )


@admin_bp.route("/jobs/<int:job_id>/approve", methods=["PUT"])
@admin_required
def approve_job(current_user, job_id):
    """Approves a pending job posting and publishes it to the student marketplace."""
    job = Job.query.get(job_id)
    if not job:
        return error_response("Job posting not found.", 404)

    job.status = "Published"
    job.rejection_reason = None

    # Notify recruiter
    if job.posted_by and job.posted_by.user:
        notif = Notification(
            user_id=job.posted_by.user.id,
            title="Job Posting Approved & Published",
            message=f"Your job posting '{job.title}' was approved by the placement cell and is now live for students to apply.",
            type="Placement",
            link="/pages/recruiter/jobs.html"
        )
        db.session.add(notif)

    db.session.commit()

    return api_response(
        message=f"Job posting '{job.title}' approved and published to the Student Marketplace!",
        data={"id": job.id, "title": job.title, "status": job.status},
        status_code=200
    )


@admin_bp.route("/jobs/<int:job_id>/reject", methods=["PUT"])
@admin_required
def reject_job(current_user, job_id):
    """Rejects a pending job posting with feedback/rejection reason."""
    job = Job.query.get(job_id)
    if not job:
        return error_response("Job posting not found.", 404)

    data = request.get_json() or {}
    reason = data.get("reason", "").strip() or "Does not meet institutional placement standards."

    job.status = "Rejected"
    job.rejection_reason = reason

    # Notify recruiter
    if job.posted_by and job.posted_by.user:
        notif = Notification(
            user_id=job.posted_by.user.id,
            title="Job Posting Moderation Update",
            message=f"Your job posting '{job.title}' was rejected by the placement cell. Reason: {reason}",
            type="Placement",
            link="/pages/recruiter/jobs.html"
        )
        db.session.add(notif)

    db.session.commit()

    return api_response(
        message=f"Job posting '{job.title}' has been rejected.",
        data={"id": job.id, "title": job.title, "status": job.status, "reason": job.rejection_reason},
        status_code=200
    )


# =====================================================================
# 6. PLACEMENT DRIVES WORKFLOW MANAGEMENT
# =====================================================================
# Stages: Company -> Eligibility -> Registration -> Shortlisting -> Assessment -> Interview -> Selection -> Offer

DRIVE_STAGES = ["Registration", "Shortlisting", "Assessment", "Interview", "Selection", "Offer", "Completed"]

@admin_bp.route("/drives", methods=["POST"])
@admin_required
def create_placement_drive(current_user):
    """
    Creates a new campus recruitment drive with eligibility criteria:
    - Company, title, academic year, drive date.
    - Eligibility: Minimum CGPA, Maximum Backlogs, Eligible Departments, Graduation Batch Year, Required Skills.
    """
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    company_id = data.get("company_id")
    academic_year = data.get("academic_year", "2025-2026").strip()
    drive_date_raw = data.get("drive_date")
    eligible_batch = data.get("eligible_batch") or data.get("batch_year")

    if not title or not company_id or not drive_date_raw or not eligible_batch:
        return error_response("Title, company, drive date, and eligible batch year are required.", 400)

    company = Company.query.get(company_id)
    if not company:
        return error_response("Company not found.", 404)

    try:
        drive_date = datetime.fromisoformat(drive_date_raw.replace("Z", "+00:00"))
    except Exception:
        drive_date = datetime.now(timezone.utc)

    # Convert branches/departments list or str
    raw_depts = data.get("eligible_departments") or data.get("branches") or ""
    if isinstance(raw_depts, list):
        eligible_departments = ", ".join(raw_depts)
    else:
        eligible_departments = str(raw_depts).strip()

    # Convert required skills list or str
    raw_skills = data.get("required_skills") or data.get("skills") or ""
    if isinstance(raw_skills, list):
        required_skills = ", ".join(raw_skills)
    else:
        required_skills = str(raw_skills).strip()

    package_ctc = str(data.get("package_ctc", "")).strip()

    drive = PlacementDrive(
        company_id=company.id,
        title=title,
        academic_year=academic_year,
        drive_date=drive_date,
        eligible_batch=int(eligible_batch),
        min_cgpa=float(data.get("min_cgpa", 0.0)),
        max_backlogs=int(data.get("max_backlogs", 0)),
        eligible_departments=eligible_departments,
        job_role=data.get("job_role", "Software Engineer").strip(),
        package_ctc=package_ctc,
        required_skills=required_skills,
        current_stage="Registration",
        status="Scheduled"
    )
    db.session.add(drive)
    db.session.commit()

    return api_response(
        message=f"Placement drive '{drive.title}' created successfully in 'Registration' stage.",
        data={"id": drive.id, "title": drive.title, "stage": drive.current_stage},
        status_code=201
    )


@admin_bp.route("/drives", methods=["GET"])
@admin_required
def list_placement_drives(current_user):
    """Lists all placement drives with registered candidates count and stage progress."""
    drives = PlacementDrive.query.order_by(PlacementDrive.drive_date.desc()).all()
    results = []

    for d in drives:
        total_registered = len(d.participating_students)
        shortlisted_count = len([s for s in d.participating_students if s.stage in ["Shortlisted", "Assessment", "Interview", "Selection", "Offer"]])
        offered_count = len([s for s in d.participating_students if s.stage in ["Offered", "Selected"]])

        results.append({
            "id": d.id,
            "title": d.title,
            "company": {
                "id": d.company.id if d.company else None,
                "name": d.company.name if d.company else "Unknown"
            },
            "job_role": d.job_role,
            "package_ctc": d.package_ctc,
            "academic_year": d.academic_year,
            "drive_date": d.drive_date.strftime("%b %d, %Y %I:%M %p") if d.drive_date else None,
            "eligible_batch": d.eligible_batch,
            "min_cgpa": float(d.min_cgpa) if d.min_cgpa else 0.0,
            "max_backlogs": d.max_backlogs,
            "eligible_departments": d.eligible_departments,
            "required_skills": d.required_skills,
            "current_stage": d.current_stage,
            "status": d.status,
            "candidates_registered": total_registered,
            "candidates_shortlisted": shortlisted_count,
            "candidates_offered": offered_count
        })

    return api_response(
        message="Placement drives retrieved successfully.",
        data={"total": len(results), "drives": results},
        status_code=200
    )


@admin_bp.route("/drives/<int:drive_id>", methods=["GET"])
@admin_required
def get_drive_details(current_user, drive_id):
    """Retrieves full drive details, criteria, and stage-by-stage candidate rosters."""
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return error_response("Placement drive not found.", 404)

    participants = []
    for p in drive.participating_students:
        s = p.student
        latest_res = Resume.query.filter_by(student_id=s.id).order_by(Resume.created_at.desc()).first()
        ats_score = float(latest_res.analysis.ats_score) if (latest_res and latest_res.analysis and latest_res.analysis.ats_score is not None) else None

        participants.append({
            "student_id": s.id,
            "roll_number": s.roll_number,
            "name": f"{s.first_name} {s.last_name}",
            "email": s.user.email if s.user else "",
            "department": s.department,
            "cgpa": float(s.cgpa) if s.cgpa else None,
            "backlogs": s.backlogs,
            "resume_score": ats_score,
            "registration_status": p.registration_status,
            "stage": p.stage,
            "offered_ctc": float(p.offered_ctc) if p.offered_ctc else None,
            "notes": p.notes,
            "registered_at": p.created_at.strftime("%b %d, %Y") if p.created_at else None
        })

    # Stage counts summary
    stage_breakdown = {}
    for st in DRIVE_STAGES:
        stage_breakdown[st] = len([p for p in participants if p["stage"] == st])
    stage_breakdown["Rejected"] = len([p for p in participants if p["stage"] == "Rejected"])

    return api_response(
        message="Placement drive details retrieved successfully.",
        data={
            "id": drive.id,
            "title": drive.title,
            "company": {
                "id": drive.company.id if drive.company else None,
                "name": drive.company.name if drive.company else "Unknown",
                "industry": drive.company.industry_type if drive.company else None
            },
            "job_role": drive.job_role,
            "package_ctc": drive.package_ctc,
            "academic_year": drive.academic_year,
            "drive_date": drive.drive_date.strftime("%b %d, %Y %I:%M %p") if drive.drive_date else None,
            "eligible_batch": drive.eligible_batch,
            "min_cgpa": float(drive.min_cgpa) if drive.min_cgpa else 0.0,
            "max_backlogs": drive.max_backlogs,
            "eligible_departments": drive.eligible_departments,
            "required_skills": drive.required_skills,
            "current_stage": drive.current_stage,
            "status": drive.status,
            "stage_breakdown": stage_breakdown,
            "candidates": participants
        },
        status_code=200
    )


@admin_bp.route("/drives/<int:drive_id>/eligible-students", methods=["GET"])
@admin_required
def get_drive_eligible_students(current_user, drive_id):
    """
    Computes and returns students matching the drive's eligibility criteria:
    - Graduation batch match
    - CGPA >= minimum threshold
    - Backlogs <= maximum allowed
    - Department in eligible departments (if specified)
    - Skills match (if specified)
    """
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return error_response("Placement drive not found.", 404)

    query = Student.query.filter_by(batch_year=drive.eligible_batch)

    if drive.min_cgpa:
        query = query.filter(or_(Student.cgpa >= drive.min_cgpa, Student.cgpa.is_(None)))

    if drive.max_backlogs is not None:
        query = query.filter(Student.backlogs <= drive.max_backlogs)

    students = query.all()

    # Department filter parsing
    eligible_depts = [d.strip().lower() for d in (drive.eligible_departments or "").split(",") if d.strip()]

    # Required skills parsing
    req_skills = [s.strip().lower() for s in (drive.required_skills or "").split(",") if s.strip()]

    already_registered_ids = set([p.student_id for p in drive.participating_students])

    eligible_list = []
    for s in students:
        if eligible_depts and s.department.lower() not in eligible_depts:
            continue

        student_skills = [sk.skill.name.lower() for sk in s.student_skills if sk.skill]
        skills_matched = []
        if req_skills:
            for rs in req_skills:
                if any(rs in sk for sk in student_skills):
                    skills_matched.append(rs)

        eligible_list.append({
            "id": s.id,
            "roll_number": s.roll_number,
            "name": f"{s.first_name} {s.last_name}",
            "email": s.user.email if s.user else "",
            "department": s.department,
            "cgpa": float(s.cgpa) if s.cgpa else None,
            "backlogs": s.backlogs,
            "skills": [sk.skill.name for sk in s.student_skills if sk.skill],
            "skills_matched": skills_matched,
            "is_registered": s.id in already_registered_ids
        })

    return api_response(
        message="Eligible students evaluated successfully.",
        data={
            "drive_id": drive.id,
            "total_eligible": len(eligible_list),
            "eligible_students": eligible_list
        },
        status_code=200
    )


@admin_bp.route("/drives/<int:drive_id>/register-student", methods=["POST"])
@admin_required
def register_student_to_drive(current_user, drive_id):
    """Registers an eligible student into the placement drive."""
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return error_response("Placement drive not found.", 404)

    data = request.get_json() or {}
    student_id = data.get("student_id")
    if not student_id:
        return error_response("student_id is required.", 400)

    student = Student.query.get(student_id)
    if not student:
        return error_response("Student not found.", 404)

    existing = PlacementDriveStudent.query.filter_by(drive_id=drive.id, student_id=student.id).first()
    if existing:
        return error_response("Student is already registered for this drive.", 409)

    participant = PlacementDriveStudent(
        drive_id=drive.id,
        student_id=student.id,
        registration_status="Registered",
        stage="Registration",
        shortlisted=False
    )
    db.session.add(participant)

    # Notify student
    if student.user:
        notif = Notification(
            user_id=student.user.id,
            title=f"Registered for Placement Drive: {drive.title}",
            message=f"You have been registered for the on-campus recruitment drive with {drive.company.name if drive.company else 'Recruiter'}.",
            type="Placement",
            link="/pages/student/dashboard.html"
        )
        db.session.add(notif)

    db.session.commit()

    return api_response(
        message=f"Student '{student.first_name} {student.last_name}' registered for drive.",
        data={"drive_id": drive.id, "student_id": student.id, "stage": participant.stage},
        status_code=201
    )


@admin_bp.route("/drives/<int:drive_id>/stage", methods=["PUT"])
@admin_required
def advance_drive_workflow_stage(current_user, drive_id):
    """
    Advances the overall placement drive workflow stage:
    Registration -> Shortlisting -> Assessment -> Interview -> Selection -> Offer -> Completed
    """
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return error_response("Placement drive not found.", 404)

    data = request.get_json() or {}
    new_stage = data.get("stage")
    if new_stage not in DRIVE_STAGES:
        return error_response(f"Invalid stage. Must be one of: {', '.join(DRIVE_STAGES)}", 400)

    drive.current_stage = new_stage
    if new_stage == "Completed":
        drive.status = "Completed"
    elif drive.status == "Scheduled":
        drive.status = "Ongoing"

    db.session.commit()

    return api_response(
        message=f"Drive '{drive.title}' advanced to '{new_stage}' stage.",
        data={"id": drive.id, "current_stage": drive.current_stage, "status": drive.status},
        status_code=200
    )


@admin_bp.route("/drives/<int:drive_id>/students/<int:student_id>/stage", methods=["PUT"])
@admin_required
def update_candidate_drive_stage(current_user, drive_id, student_id):
    """
    Advances or modifies an individual candidate's progression in a drive:
    - Stage options: 'Shortlisted', 'Assessment', 'Interview', 'Selected', 'Offered', 'Rejected'.
    - If moved to 'Offered' or 'Selected' with offered_ctc, automatically records official PlacementRecord!
    """
    participant = PlacementDriveStudent.query.filter_by(drive_id=drive_id, student_id=student_id).first()
    if not participant:
        return error_response("Student is not registered in this drive.", 404)

    data = request.get_json() or {}
    new_stage = data.get("stage")
    notes = data.get("notes")
    offered_ctc = data.get("offered_ctc")

    valid_stages = ["Registration", "Shortlisted", "Assessment", "Interview", "Selected", "Offered", "Rejected"]
    if new_stage not in valid_stages:
        return error_response(f"Invalid stage. Allowed: {', '.join(valid_stages)}", 400)

    participant.stage = new_stage
    if notes is not None:
        participant.notes = notes
    if offered_ctc is not None:
        participant.offered_ctc = float(offered_ctc)

    if new_stage in ["Shortlisted", "Assessment", "Interview", "Selected", "Offered"]:
        participant.shortlisted = True

    # Automatic PlacementRecord creation if student is offered
    if new_stage in ["Offered", "Selected"]:
        drive = participant.drive
        package_num = float(offered_ctc) if offered_ctc else (
            float(drive.package_ctc.replace("₹", "").replace("LPA", "").strip()) if (drive.package_ctc and drive.package_ctc.replace(".", "").replace("₹", "").replace("LPA", "").strip().isdigit()) else 6.0
        )

        existing_record = PlacementRecord.query.filter_by(
            student_id=participant.student_id,
            company_id=drive.company_id
        ).first()

        if not existing_record:
            official_record = PlacementRecord(
                student_id=participant.student_id,
                company_id=drive.company_id,
                package_ctc=package_num,
                offer_date=datetime.now(timezone.utc).date(),
                acceptance_status="Accepted"
            )
            db.session.add(official_record)

        # Notify student of offer
        student = participant.student
        if student and student.user:
            notif = Notification(
                user_id=student.user.id,
                title=f"Placement Offer: {drive.company.name if drive.company else 'Campus Partner'}",
                message=f"Congratulations! You have received a placement offer for {drive.job_role} with an offered CTC of ₹{package_num} LPA.",
                type="Placement",
                link="/pages/student/applications.html"
            )
            db.session.add(notif)

    db.session.commit()

    return api_response(
        message=f"Candidate stage updated to '{new_stage}'.",
        data={
            "student_id": participant.student_id,
            "stage": participant.stage,
            "offered_ctc": float(participant.offered_ctc) if participant.offered_ctc else None
        },
        status_code=200
    )


# =====================================================================
# 7. CAMPUS WORKSHOPS MONITORING
# =====================================================================

@admin_bp.route("/workshops", methods=["GET"])
@admin_required
def list_all_workshops(current_user):
    """Retrieves all technical workshops, webinars, and masterclasses hosted on campus."""
    workshops = Workshop.query.order_by(Workshop.start_time.desc()).all()
    results = []

    for w in workshops:
        results.append({
            "id": w.id,
            "title": w.title,
            "description": w.description,
            "instructor": {
                "name": w.instructor.name if w.instructor else (w.company.name if w.company else "Industry Expert"),
                "company": w.company.name if w.company else "Tech Partner"
            },
            "start_time": w.start_time.strftime("%b %d, %Y %I:%M %p") if w.start_time else None,
            "end_time": w.end_time.strftime("%b %d, %Y %I:%M %p") if w.end_time else None,
            "venue_or_link": w.venue_or_link,
            "max_capacity": w.max_capacity,
            "registered_count": len(w.registrations),
            "created_at": w.created_at.strftime("%b %d, %Y") if w.created_at else None
        })

    return api_response(
        message="Workshops retrieved successfully.",
        data={"total": len(results), "workshops": results},
        status_code=200
    )


# =====================================================================
# 8. ALUMNI DIRECTORY & MENTORSHIP NETWORK
# =====================================================================

@admin_bp.route("/alumni", methods=["GET"])
@admin_required
def list_alumni(current_user):
    """Filterable alumni directory with company, role, batch year, and mentorship availability."""
    search = request.args.get("search", "").strip().lower()
    dept = request.args.get("department")
    batch = request.args.get("graduation_year", type=int)

    query = Alumni.query
    if dept:
        query = query.filter_by(department=dept)
    if batch:
        query = query.filter_by(graduation_year=batch)

    alumni_list = query.order_by(Alumni.graduation_year.desc(), Alumni.name.asc()).all()
    results = []

    for a in alumni_list:
        if search and (search not in a.name.lower() and search not in (a.current_company or "").lower() and search not in (a.current_role or "").lower()):
            continue

        results.append({
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "graduation_year": a.graduation_year,
            "department": a.department,
            "current_company": a.current_company,
            "current_role": a.current_role,
            "linkedin_url": a.linkedin_url,
            "willing_to_mentor": a.willing_to_mentor,
            "student_id": a.student_id
        })

    return api_response(
        message="Alumni directory retrieved successfully.",
        data={"total": len(results), "alumni": results},
        status_code=200
    )


@admin_bp.route("/alumni", methods=["POST"])
@admin_required
def add_alumni(current_user):
    """Adds a new alumni profile to the institution's networking database."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    year = data.get("graduation_year")

    if not name or not email or not year:
        return error_response("Name, email, and graduation year are required.", 400)

    alumnus = Alumni(
        name=name,
        email=email,
        graduation_year=int(year),
        department=data.get("department", "").strip(),
        current_company=data.get("current_company", "").strip(),
        current_role=data.get("current_role", "").strip(),
        linkedin_url=data.get("linkedin_url", "").strip(),
        willing_to_mentor=bool(data.get("willing_to_mentor", True)),
        student_id=data.get("student_id")
    )
    db.session.add(alumnus)
    db.session.commit()

    return api_response(
        message=f"Alumni record for '{alumnus.name}' added successfully.",
        data={"id": alumnus.id, "name": alumnus.name},
        status_code=201
    )


@admin_bp.route("/alumni/<int:alumni_id>", methods=["PUT"])
@admin_required
def update_alumni(current_user, alumni_id):
    """Updates an alumni's professional details or mentorship status."""
    alumnus = Alumni.query.get(alumni_id)
    if not alumnus:
        return error_response("Alumni record not found.", 404)

    data = request.get_json() or {}
    for field in ["name", "email", "department", "current_company", "current_role", "linkedin_url"]:
        if field in data:
            setattr(alumnus, field, data[field].strip())
    if "graduation_year" in data:
        alumnus.graduation_year = int(data["graduation_year"])
    if "willing_to_mentor" in data:
        alumnus.willing_to_mentor = bool(data["willing_to_mentor"])

    db.session.commit()
    return api_response(
        message=f"Alumni record for '{alumnus.name}' updated.",
        data={"id": alumnus.id, "name": alumnus.name},
        status_code=200
    )


# =====================================================================
# 9. BROADCAST ANNOUNCEMENTS & AUTOMATED NOTIFICATION DISPATCHER
# =====================================================================

@admin_bp.route("/announcements", methods=["POST"])
@admin_required
def create_announcement(current_user):
    """
    Broadcasts an institutional placement notice to all students, specific departments, or specific batch years.
    Automatically dispatches corresponding user Notifications to target students.
    """
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    audience = data.get("target_audience", "ALL").upper()  # ALL, DEPARTMENT, BATCH
    target_value = data.get("target_value", "").strip()
    priority = data.get("priority", "Normal")

    if not title or not content:
        return error_response("Title and content are required.", 400)

    announcement = Announcement(
        title=title,
        content=content,
        target_audience=audience,
        target_value=target_value if audience != "ALL" else None,
        priority=priority,
        posted_by_id=current_user.id
    )
    db.session.add(announcement)

    # Find recipient students
    target_query = Student.query
    if audience == "DEPARTMENT" and target_value:
        target_query = target_query.filter(func.lower(Student.department) == target_value.lower())
    elif audience == "BATCH" and target_value.isdigit():
        target_query = target_query.filter_by(batch_year=int(target_value))

    target_students = target_query.all()
    created_notifications_count = 0

    for s in target_students:
        if s.user:
            notif = Notification(
                user_id=s.user.id,
                title=f"Placement Notice: {title}",
                message=content[:200] + ("..." if len(content) > 200 else ""),
                type="General",
                link="/pages/student/dashboard.html"
            )
            db.session.add(notif)
            created_notifications_count += 1

    db.session.commit()

    return api_response(
        message=f"Announcement broadcast successfully to {created_notifications_count} students.",
        data={
            "id": announcement.id,
            "title": announcement.title,
            "audience": announcement.target_audience,
            "recipients_count": created_notifications_count,
            "created_at": announcement.created_at.strftime("%b %d, %Y")
        },
        status_code=201
    )


@admin_bp.route("/announcements", methods=["GET"])
@admin_required
def list_announcements(current_user):
    """Lists all past broadcast placement announcements."""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    results = []

    for a in announcements:
        admin_name = "Placement Cell"
        if a.posted_by and a.posted_by.admin_profile:
            admin_name = f"{a.posted_by.admin_profile.first_name} {a.posted_by.admin_profile.last_name}"
        elif a.posted_by:
            admin_name = a.posted_by.email

        results.append({
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "target_audience": a.target_audience,
            "target_value": a.target_value,
            "priority": a.priority,
            "posted_by": admin_name,
            "created_at": a.created_at.strftime("%b %d, %Y %I:%M %p") if a.created_at else None
        })

    return api_response(
        message="Announcements retrieved successfully.",
        data={"total": len(results), "announcements": results},
        status_code=200
    )


# =====================================================================
# 10. PLACEMENT SUMMARY REPORTS & CSV EXPORTS
# =====================================================================

@admin_bp.route("/reports/summary", methods=["GET"])
@admin_required
def get_placement_report_summary(current_user):
    """
    Generates a high-level institutional placement report JSON payload suitable for presentations and auditing.
    """
    total_students = Student.query.count()
    placed_student_ids = set([
        r[0] for r in db.session.query(PlacementRecord.student_id).filter(
            PlacementRecord.acceptance_status != "Declined"
        ).distinct().all()
    ])
    selected_app_student_ids = set([
        r[0] for r in db.session.query(Application.student_id).filter(
            Application.current_status == "SELECTED"
        ).distinct().all()
    ])
    drive_offered_student_ids = set([
        r[0] for r in db.session.query(PlacementDriveStudent.student_id).filter(
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).distinct().all()
    ])
    all_placed_ids = placed_student_ids.union(selected_app_student_ids).union(drive_offered_student_ids)

    placed_count = len(all_placed_ids)
    placement_rate = round((placed_count / total_students * 100), 1) if total_students > 0 else 0.0

    # CTC calculations
    all_ctcs = [
        float(r.package_ctc) for r in PlacementRecord.query.filter(
            PlacementRecord.package_ctc.isnot(None),
            PlacementRecord.acceptance_status != "Declined"
        ).all()
    ] + [
        float(p.offered_ctc) for p in PlacementDriveStudent.query.filter(
            PlacementDriveStudent.offered_ctc.isnot(None),
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).all()
    ]

    avg_ctc = round(sum(all_ctcs) / len(all_ctcs), 2) if all_ctcs else 0.0
    highest_ctc = round(max(all_ctcs), 2) if all_ctcs else 0.0

    # Salary tiers
    tier_super_dream = len([c for c in all_ctcs if c >= 15.0])   # >= 15 LPA
    tier_dream = len([c for c in all_ctcs if 8.0 <= c < 15.0])    # 8 - 15 LPA
    tier_standard = len([c for c in all_ctcs if c < 8.0])        # < 8 LPA

    return api_response(
        message="Institutional placement report summary generated successfully.",
        data={
            "institution": "College Placement & Career Development Cell",
            "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y %I:%M %p UTC"),
            "metrics": {
                "total_students": total_students,
                "placed_students": placed_count,
                "unplaced_students": total_students - placed_count,
                "placement_rate_percent": placement_rate,
                "average_ctc_lpa": avg_ctc,
                "highest_ctc_lpa": highest_ctc
            },
            "salary_tiers": {
                "super_dream_15plus_lpa": tier_super_dream,
                "dream_8_to_15_lpa": tier_dream,
                "standard_below_8_lpa": tier_standard
            },
            "total_companies_participated": Company.query.count(),
            "total_drives_conducted": PlacementDrive.query.count()
        },
        status_code=200
    )


@admin_bp.route("/reports/export/students-csv", methods=["GET"])
@admin_required
def export_students_csv(current_user):
    """Generates and downloads a complete CSV roster of all students with placement outcomes."""
    students = Student.query.order_by(Student.department.asc(), Student.roll_number.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll Number",
        "Student Name",
        "Email",
        "Department",
        "Degree",
        "Batch Year",
        "CGPA",
        "Backlogs",
        "Placement Status",
        "Recruiting Company",
        "Package CTC (LPA)",
        "Resume ATS Score (%)",
        "Total Applications"
    ])

    for s in students:
        rec = PlacementRecord.query.filter_by(student_id=s.id).filter(
            PlacementRecord.acceptance_status != "Declined"
        ).first()

        drive_off = PlacementDriveStudent.query.filter_by(student_id=s.id).filter(
            PlacementDriveStudent.stage.in_(["Offered", "Selected"])
        ).first()

        app_sel = Application.query.filter_by(student_id=s.id, current_status="SELECTED").first()

        if rec:
            status = "Placed"
            company = rec.company.name if rec.company else "Company"
            ctc = float(rec.package_ctc)
        elif drive_off:
            status = "Placed (Drive)"
            company = drive_off.drive.company.name if (drive_off.drive and drive_off.drive.company) else "Drive Partner"
            ctc = float(drive_off.offered_ctc) if drive_off.offered_ctc else "Selected"
        elif app_sel:
            status = "Placed (Direct)"
            company = app_sel.job.company.name if (app_sel.job and app_sel.job.company) else "Job Recruiter"
            ctc = app_sel.job.ctc or "Selected"
        else:
            status = "Unplaced"
            company = "-"
            ctc = "-"

        latest_res = Resume.query.filter_by(student_id=s.id).order_by(Resume.created_at.desc()).first()
        ats = float(latest_res.analysis.ats_score) if (latest_res and latest_res.analysis and latest_res.analysis.ats_score is not None) else "N/A"

        writer.writerow([
            s.roll_number,
            f"{s.first_name} {s.last_name}",
            s.user.email if s.user else "",
            s.department,
            s.degree,
            s.batch_year,
            float(s.cgpa) if s.cgpa else "N/A",
            s.backlogs,
            status,
            company,
            ctc,
            ats,
            len(s.applications)
        ])

    csv_data = output.getvalue()
    filename = f"placement_students_roster_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@admin_bp.route("/reports/export/departments-csv", methods=["GET"])
@admin_required
def export_departments_csv(current_user):
    """Generates and downloads a department-by-department placement statistics CSV."""
    departments = db.session.query(Student.department).distinct().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Department",
        "Total Students",
        "Placed Students",
        "Unplaced Students",
        "Placement Rate (%)",
        "Average CTC (LPA)",
        "Highest CTC (LPA)"
    ])

    for (dept,) in departments:
        if not dept:
            continue
        students = Student.query.filter_by(department=dept).all()
        dept_total = len(students)
        dept_placed = 0
        ctcs = []

        for s in students:
            rec = PlacementRecord.query.filter_by(student_id=s.id).filter(
                PlacementRecord.acceptance_status != "Declined"
            ).first()
            if rec:
                dept_placed += 1
                if rec.package_ctc:
                    ctcs.append(float(rec.package_ctc))
            elif Application.query.filter_by(student_id=s.id, current_status="SELECTED").first():
                dept_placed += 1

        rate = round((dept_placed / dept_total * 100), 1) if dept_total > 0 else 0.0
        avg_ctc = round(sum(ctcs) / len(ctcs), 2) if ctcs else 0.0
        high_ctc = round(max(ctcs), 2) if ctcs else 0.0

        writer.writerow([
            dept,
            dept_total,
            dept_placed,
            dept_total - dept_placed,
            f"{rate}%",
            avg_ctc,
            high_ctc
        ])

    csv_data = output.getvalue()
    filename = f"placement_department_stats_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@admin_bp.route("/reports/export/at-risk-csv", methods=["GET"])
@admin_required
def export_at_risk_csv(current_user):
    """Generates and downloads a CSV of all identified at-risk students requiring interventions."""
    at_risk_list = compute_at_risk_students()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll Number",
        "Student Name",
        "Email",
        "Department",
        "Batch Year",
        "CGPA",
        "Backlogs",
        "Resume ATS Score (%)",
        "Total Applications",
        "Rejections",
        "Risk Severity",
        "Identified Risk Indicators",
        "Interventions Recorded"
    ])

    for ar in at_risk_list:
        writer.writerow([
            ar["roll_number"],
            ar["name"],
            ar["email"],
            ar["department"],
            ar["batch_year"],
            ar["cgpa"] if ar["cgpa"] is not None else "N/A",
            ar["backlogs"],
            ar["resume_score"],
            ar["total_applications"],
            ar["rejections"],
            ar["severity"],
            "; ".join(ar["indicators"]),
            ar["interventions_count"]
        ])

    csv_data = output.getvalue()
    filename = f"at_risk_students_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# =====================================================================
# 11. BULK TARGETED COMMUNICATIONS & MULTI-CHANNEL DISPATCH
# =====================================================================

@admin_bp.route("/communications/broadcast", methods=["POST"])
@admin_required
def broadcast_bulk_communication(current_user):
    """
    Sends targeted announcements via in-app notifications and email.
    Target cohorts:
    - 'all': All registered students
    - 'branch': Specific engineering branch/department
    - 'year': Specific graduation batch year
    - 'eligible_drive': Students meeting eligibility criteria for a specific drive
    - 'domain': Students having matching domain/skill interest
    - 'registered_drive': Students registered for a specific placement drive
    - 'registered_workshop': Students registered for a workshop

    Channels:
    - 'both': In-app notifications + email
    - 'in_app': In-app notifications only
    - 'email': Email dispatch only
    """
    data = request.get_json() or {}
    target_type = data.get("target_type", "all").lower()
    target_value = data.get("target_value")
    title = data.get("title", "").strip()
    message = data.get("message", "").strip()
    link = data.get("link", "/pages/student/dashboard.html")
    channel = data.get("channel", "both").lower()

    if not title or not message:
        return error_response("Title and message are required.", 400)

    # Delegate bulk dispatch to NotificationService (keeps route logic decoupled)
    result = NotificationService.send_bulk_notification(
        target_type=target_type,
        target_value=target_value,
        title=title,
        message=message,
        link=link,
        channel=channel,
        notif_type="Broadcast"
    )

    # Also log to Announcement model for institutional audit logging
    announcement = Announcement(
        title=title,
        content=message,
        target_audience=target_type.upper(),
        target_value=str(target_value) if target_value else None,
        priority=data.get("priority", "Normal"),
        posted_by_id=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()

    return api_response(
        message=f"Broadcast successfully dispatched to {result['total_targeted_students']} students ({result['in_app_notifications_created']} in-app, {result['emails_dispatched']} emails).",
        data=result,
        status_code=201
    )

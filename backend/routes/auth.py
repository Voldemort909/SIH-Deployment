"""
Authentication routes for registration, login, logout, profile retrieval,
and administrator approval of industry accounts.
"""
from flask import Blueprint, request
from backend.extensions import db
from backend.models.user import User, Student, IndustryExpert, Admin
from backend.models.company import Company
from backend.utils.auth import (
    generate_token,
    token_required,
    admin_required
)
from backend.utils.response import api_response, error_response
from backend.utils.validation import (
    validate_student_registration,
    validate_industry_registration,
    validate_login
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/student/register", methods=["POST"])
def register_student():
    """
    Public registration endpoint for students.
    Creates both the central user credential and the student academic profile.
    """
    data = request.get_json(silent=True)
    is_valid, err_msg, cleaned = validate_student_registration(data)
    if not is_valid:
        return error_response(message=err_msg, status_code=400)

    # Check for duplicate email
    if User.query.filter_by(email=cleaned["email"]).first():
        return error_response(
            message="An account with this email address already exists.",
            status_code=409
        )

    # Check for duplicate roll/enrollment number
    if Student.query.filter_by(roll_number=cleaned["roll_number"]).first():
        return error_response(
            message="A student with this enrollment / roll number already exists.",
            status_code=409
        )

    try:
        # Create base User account
        user = User(
            email=cleaned["email"],
            role="student",
            is_active=True,
            is_verified=False
        )
        user.set_password(cleaned["password"])
        db.session.add(user)
        db.session.flush()  # Populates user.id

        # Create Student profile
        student = Student(
            user_id=user.id,
            roll_number=cleaned["roll_number"],
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            department=cleaned["department"],
            degree=cleaned["degree"],
            batch_year=cleaned["batch_year"],
            cgpa=cleaned["cgpa"],
            phone=cleaned["phone"],
            gender=cleaned["gender"]
        )
        db.session.add(student)
        db.session.commit()

        token = generate_token(user)

        return api_response(
            message="Student registered successfully.",
            data={
                "token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "student_profile": {
                        "id": student.id,
                        "roll_number": student.roll_number,
                        "name": f"{student.first_name} {student.last_name}".strip(),
                        "department": student.department,
                        "degree": student.degree,
                        "batch_year": student.batch_year,
                        "cgpa": float(student.cgpa) if student.cgpa is not None else None
                    }
                }
            },
            status_code=201
        )
    except Exception as exc:
        db.session.rollback()
        return error_response(
            message="An unexpected error occurred during student registration.",
            status_code=500,
            error_details=str(exc)
        )


@auth_bp.route("/industry/register", methods=["POST"])
def register_industry():
    """
    Public registration endpoint for industry experts and recruiters.
    Account is created with status = 'PENDING'.
    Requires placement cell administrator approval before gaining full access.
    """
    data = request.get_json(silent=True)
    is_valid, err_msg, cleaned = validate_industry_registration(data)
    if not is_valid:
        return error_response(message=err_msg, status_code=400)

    # Check for duplicate email
    if User.query.filter_by(email=cleaned["email"]).first():
        return error_response(
            message="An account with this email address already exists.",
            status_code=409
        )

    try:
        # Find or create company
        company = Company.query.filter_by(name=cleaned["company_name"]).first()
        if not company:
            company = Company(name=cleaned["company_name"])
            db.session.add(company)
            db.session.flush()

        # Create base User account
        user = User(
            email=cleaned["email"],
            role="industry_expert",
            is_active=True,
            is_verified=False
        )
        user.set_password(cleaned["password"])
        db.session.add(user)
        db.session.flush()

        # Create IndustryExpert profile with PENDING status
        expert = IndustryExpert(
            user_id=user.id,
            company_id=company.id,
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            designation=cleaned["designation"],
            experience_years=cleaned["experience_years"],
            linkedin_url=cleaned["linkedin_url"],
            status="PENDING"
        )
        db.session.add(expert)
        db.session.commit()

        token = generate_token(user)

        return api_response(
            message="Registration submitted successfully. Your industry account is PENDING administrator approval.",
            data={
                "token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "expert_profile": {
                        "id": expert.id,
                        "name": f"{expert.first_name} {expert.last_name}".strip(),
                        "designation": expert.designation,
                        "company": company.name,
                        "status": expert.status
                    }
                }
            },
            status_code=201
        )
    except Exception as exc:
        db.session.rollback()
        return error_response(
            message="An unexpected error occurred during industry registration.",
            status_code=500,
            error_details=str(exc)
        )


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Unified login endpoint for all roles (student, industry_expert, admin).
    Verifies password hash and returns signed JWT token.
    """
    data = request.get_json(silent=True)
    is_valid, err_msg, cleaned = validate_login(data)
    if not is_valid:
        return error_response(message=err_msg, status_code=400)

    user = User.query.filter_by(email=cleaned["email"]).first()
    if not user or not user.check_password(cleaned["password"]):
        return error_response(
            message="Invalid email or password.",
            status_code=401
        )

    if not user.is_active:
        return error_response(
            message="Your account has been deactivated. Please contact the college placement cell.",
            status_code=403
        )

    # Build role-specific metadata
    user_payload = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified
    }

    if user.role == "student" and user.student_profile:
        sp = user.student_profile
        user_payload["profile"] = {
            "id": sp.id,
            "roll_number": sp.roll_number,
            "name": f"{sp.first_name} {sp.last_name}".strip(),
            "department": sp.department,
            "batch_year": sp.batch_year,
            "cgpa": float(sp.cgpa) if sp.cgpa is not None else None
        }
    elif user.role == "industry_expert" and user.expert_profile:
        ep = user.expert_profile
        user_payload["profile"] = {
            "id": ep.id,
            "name": f"{ep.first_name} {ep.last_name}".strip(),
            "designation": ep.designation,
            "company": ep.company.name if ep.company else None,
            "status": ep.status
        }
    elif user.role == "admin" and user.admin_profile:
        ap = user.admin_profile
        user_payload["profile"] = {
            "id": ap.id,
            "staff_id": ap.staff_id,
            "name": f"{ap.first_name} {ap.last_name}".strip(),
            "designation": ap.designation,
            "department": ap.department
        }

    token = generate_token(user)

    return api_response(
        message="Login successful.",
        data={
            "token": token,
            "user": user_payload
        },
        status_code=200
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Stateless logout acknowledgment endpoint.
    Instructs the frontend client to discard the JWT token.
    """
    return api_response(
        message="Logged out successfully. Please remove your token from client storage.",
        status_code=200
    )


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    """
    Returns the authenticated user's profile details.
    Requires valid Bearer token.
    """
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

    if current_user.role == "student" and current_user.student_profile:
        sp = current_user.student_profile
        user_data["student_profile"] = {
            "id": sp.id,
            "roll_number": sp.roll_number,
            "first_name": sp.first_name,
            "last_name": sp.last_name,
            "full_name": f"{sp.first_name} {sp.last_name}".strip(),
            "department": sp.department,
            "degree": sp.degree,
            "batch_year": sp.batch_year,
            "cgpa": float(sp.cgpa) if sp.cgpa is not None else None,
            "phone": sp.phone,
            "gender": sp.gender
        }
    elif current_user.role == "industry_expert" and current_user.expert_profile:
        ep = current_user.expert_profile
        user_data["expert_profile"] = {
            "id": ep.id,
            "first_name": ep.first_name,
            "last_name": ep.last_name,
            "full_name": f"{ep.first_name} {ep.last_name}".strip(),
            "designation": ep.designation,
            "company_name": ep.company.name if ep.company else None,
            "experience_years": ep.experience_years,
            "linkedin_url": ep.linkedin_url,
            "status": ep.status
        }
    elif current_user.role == "admin" and current_user.admin_profile:
        ap = current_user.admin_profile
        user_data["admin_profile"] = {
            "id": ap.id,
            "first_name": ap.first_name,
            "last_name": ap.last_name,
            "full_name": f"{ap.first_name} {ap.last_name}".strip(),
            "staff_id": ap.staff_id,
            "designation": ap.designation,
            "department": ap.department
        }

    return api_response(
        message="Profile retrieved successfully.",
        data={"user": user_data},
        status_code=200
    )


# --- Administrator Approval Routes for Industry Accounts ---

@auth_bp.route("/admin/pending-industry", methods=["GET"])
@admin_required
def list_pending_industry(current_user):
    """
    Admin-only endpoint: List all industry experts awaiting verification.
    """
    pending = IndustryExpert.query.filter_by(status="PENDING").all()
    results = [
        {
            "id": exp.id,
            "user_id": exp.user_id,
            "name": f"{exp.first_name} {exp.last_name}".strip(),
            "email": exp.user.email if exp.user else None,
            "company": exp.company.name if exp.company else None,
            "designation": exp.designation,
            "experience_years": exp.experience_years,
            "linkedin_url": exp.linkedin_url,
            "status": exp.status,
            "applied_at": exp.created_at.isoformat() if exp.created_at else None
        }
        for exp in pending
    ]
    return api_response(
        message=f"Found {len(results)} pending industry account(s).",
        data={"pending_accounts": results},
        status_code=200
    )


@auth_bp.route("/admin/approve-industry/<int:expert_id>", methods=["POST"])
@admin_required
def approve_industry(current_user, expert_id):
    """
    Admin-only endpoint: Approve a pending industry expert account.
    """
    expert = db.session.get(IndustryExpert, expert_id)
    if not expert:
        return error_response("Industry expert account not found.", 404)

    expert.status = "APPROVED"
    db.session.commit()

    return api_response(
        message=f"Industry account for {expert.first_name} {expert.last_name} has been APPROVED.",
        data={
            "expert_id": expert.id,
            "status": expert.status,
            "email": expert.user.email if expert.user else None
        },
        status_code=200
    )


@auth_bp.route("/admin/reject-industry/<int:expert_id>", methods=["POST"])
@admin_required
def reject_industry(current_user, expert_id):
    """
    Admin-only endpoint: Reject a pending industry expert account.
    """
    expert = db.session.get(IndustryExpert, expert_id)
    if not expert:
        return error_response("Industry expert account not found.", 404)

    expert.status = "REJECTED"
    db.session.commit()

    return api_response(
        message=f"Industry account for {expert.first_name} {expert.last_name} has been REJECTED.",
        data={
            "expert_id": expert.id,
            "status": expert.status,
            "email": expert.user.email if expert.user else None
        },
        status_code=200
    )

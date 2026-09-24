"""
Centralized Placement & Skill Analytics API Routes.
Exposes endpoints for:
- Placement Overview & Executive Summary
- Department-wise placement metrics
- Company-wise placement benchmarks
- Multi-year historical trends
- Company-specific hiring history & timelines
- Skill Demand Analytics (market demand % vs student supply % and gap analysis)
"""
from flask import Blueprint, request
from backend.extensions import db
from backend.models.company import Company, CompanyHiringHistory
from backend.services.analytics_service import AnalyticsService
from backend.utils.auth import token_required, admin_required
from backend.utils.response import api_response, error_response

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/overview", methods=["GET"])
@token_required
def get_placement_overview(current_user):
    """
    Returns executive campus-wide placement metrics:
    overall placement rate, average CTC, highest CTC, offers,
    department breakdown, company breakdown, and multi-year trajectory.
    """
    data = AnalyticsService.get_placement_overview_analytics()
    return api_response(
        message="Placement overview analytics retrieved successfully.",
        data=data,
        status_code=200
    )


@analytics_bp.route("/departments", methods=["GET"])
@token_required
def get_department_analytics(current_user):
    """
    Returns department-specific placement rates and compensation ranges.
    """
    data = AnalyticsService.get_department_placement_analytics()
    return api_response(
        message="Department placement analytics retrieved successfully.",
        data={"departments": data},
        status_code=200
    )


@analytics_bp.route("/companies", methods=["GET"])
@token_required
def get_company_analytics(current_user):
    """
    Returns company-specific recruitment numbers and salary packages.
    """
    data = AnalyticsService.get_company_placement_analytics()
    return api_response(
        message="Company placement analytics retrieved successfully.",
        data={"companies": data},
        status_code=200
    )


@analytics_bp.route("/year-wise", methods=["GET"])
@token_required
def get_year_wise_analytics(current_user):
    """
    Returns multi-year placement performance and hiring trends.
    """
    data = AnalyticsService.get_year_wise_placement_analytics()
    return api_response(
        message="Year-wise placement trends retrieved successfully.",
        data={"years": data},
        status_code=200
    )


@analytics_bp.route("/companies/<int:company_id>/history", methods=["GET"])
@token_required
def get_company_history(current_user, company_id):
    """
    Returns multi-year historical hiring records and salary growth for a specific company.
    """
    data = AnalyticsService.get_company_hiring_history(company_id)
    if "error" in data:
        return error_response(data["error"], 404)

    return api_response(
        message=f"Hiring history retrieved for {data['company_name']}.",
        data=data,
        status_code=200
    )


@analytics_bp.route("/companies/<int:company_id>/history", methods=["POST"])
@admin_required
def add_company_history(current_user, company_id):
    """
    Admin endpoint to store historical hiring statistics for a company:
    - hiring_year
    - students_selected
    - offers_count
    - average_ctc
    - highest_ctc
    """
    company = Company.query.get(company_id)
    if not company:
        return error_response("Company not found.", 404)

    payload = request.get_json() or {}
    hiring_year = payload.get("hiring_year")
    if not hiring_year:
        return error_response("hiring_year is required.", 400)

    # Check if record for year already exists
    record = CompanyHiringHistory.query.filter_by(
        company_id=company_id, hiring_year=int(hiring_year)
    ).first()

    if not record:
        record = CompanyHiringHistory(
            company_id=company_id,
            hiring_year=int(hiring_year)
        )
        db.session.add(record)

    record.students_selected = int(payload.get("students_selected", record.students_selected or 0))
    record.offers_count = int(payload.get("offers_count", record.offers_count or record.students_selected))
    if "average_ctc" in payload:
        record.average_ctc = float(payload["average_ctc"])
    if "highest_ctc" in payload:
        record.highest_ctc = float(payload["highest_ctc"])

    db.session.commit()

    return api_response(
        message=f"Historical hiring record for {company.name} in {hiring_year} saved.",
        data=record.to_dict(),
        status_code=201
    )


@analytics_bp.route("/skills", methods=["GET"])
@token_required
def get_skill_demand_analytics(current_user):
    """
    Analyzes skill requirements across active job postings and compares industry
    demand against student skill availability to pinpoint critical skill gaps.
    """
    data = AnalyticsService.get_skill_demand_analytics()
    return api_response(
        message="Skill demand analytics retrieved successfully.",
        data=data,
        status_code=200
    )

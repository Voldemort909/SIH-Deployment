from datetime import datetime, timezone
from flask import Blueprint, current_app
from backend.utils.response import api_response

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify backend service availability.
    Accessible via: GET /api/health
    """
    return api_response(
        message="College Placement & Career Development Platform API is running",
        data={
            "service": "placement-portal-backend",
            "environment": current_app.config.get("ENV", "development"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status_code=200
    )

"""
Routes initialization and blueprint registration module.
All application route blueprints are registered through register_routes.
"""
from backend.routes.health import health_bp
from backend.routes.auth import auth_bp
from backend.routes.student import student_bp
from backend.routes.jobs import jobs_bp
from backend.routes.industry import industry_bp
from backend.routes.admin import admin_bp
from backend.routes.notifications import notifications_bp
from backend.routes.analytics import analytics_bp


def register_routes(app):
    """
    Registers all Blueprints to the Flask application instance.
    """
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(industry_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)

import os
import sys
from pathlib import Path

# Ensure project root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from backend.config import config_by_name
from backend.extensions import db, migrate, cors
from backend.routes import register_routes
from backend.utils.response import error_response, api_response


def create_app(config_name=None):
    """
    Flask Application Factory.
    Initializes and configures the Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    frontend_dir = PROJECT_ROOT / "frontend"
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    
    # Load configuration
    config_class = config_by_name.get(config_name, config_by_name["default"])
    if config_name == "production":
        if not os.getenv("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set when FLASK_ENV=production")
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be set when FLASK_ENV=production")
        if not database_url.startswith(("mysql://", "mysql+pymysql://")):
            raise RuntimeError("Production DATABASE_URL must use MySQL")
    app.config.from_object(config_class)
    app.config["ENV"] = config_name

    # Initialize extensions
    db.init_app(app)

    # Ensure all models are registered with SQLAlchemy metadata
    import backend.models  # noqa: F401

    migrate.init_app(app, db, directory=str(PROJECT_ROOT / "backend" / "migrations"))
    raw_cors = app.config.get("CORS_ORIGINS", "*")
    if isinstance(raw_cors, str):
        if raw_cors.strip() == "*":
            cors_origins = "*"
        else:
            cors_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]
    else:
        cors_origins = raw_cors

    cors.init_app(
        app,
        resources={r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "expose_headers": ["Content-Type", "Authorization"]
        }},
        supports_credentials=True
    )

    # Register blueprints / API routes
    register_routes(app)

    # Serve the frontend web application
    @app.route("/", methods=["GET"])
    def index():
        if (frontend_dir / "index.html").exists():
            return send_from_directory(frontend_dir, "index.html")
        return api_response(
            message="Welcome to the College Placement & Career Development Platform API",
            data={
                "health_check": "/api/health",
                "documentation": "Refer to README.md for endpoint details"
            }
        )

    # Friendly route dictionary for clean URLs and direct routing
    FRIENDLY_ROUTES = {
        "why-not-selected": "pages/student/why-not-selected.html",
        "placement-intelligence": "pages/student/why-not-selected.html",
        "alumni": "pages/student/alumni.html",
        "alumni-network": "pages/student/alumni.html",
        "alumni-directory": "pages/student/alumni.html",
        "student/why-not-selected": "pages/student/why-not-selected.html",
        "student/placement-intelligence": "pages/student/why-not-selected.html",
        "student/alumni": "pages/student/alumni.html",
        "student/dashboard": "pages/student/dashboard.html",
        "student/jobs": "pages/student/jobs.html",
        "student/applications": "pages/student/applications.html",
        "student/resume": "pages/student/resume-analysis.html",
        "student/resume-analysis": "pages/student/resume-analysis.html",
        "dashboard": "pages/student/dashboard.html",
        "jobs": "pages/student/jobs.html",
        "applications": "pages/student/applications.html",
        "resume": "pages/student/resume-analysis.html",
        "resume-analysis": "pages/student/resume-analysis.html",
        "resume-intelligence": "pages/student/resume-analysis.html",
        "login": "pages/login.html",
        "register": "pages/register.html",
        "recruiter": "pages/recruiter/jobs.html",
        "recruiter/jobs": "pages/recruiter/jobs.html",
        "recruiter/dashboard": "pages/recruiter/jobs.html",
        "admin": "pages/admin/dashboard.html",
        "admin/dashboard": "pages/admin/dashboard.html",
        "admin/jobs": "pages/admin/jobs.html",
        "industry": "pages/recruiter/jobs.html",
        "industry/jobs": "pages/recruiter/jobs.html",
        "industry/dashboard": "pages/recruiter/jobs.html"
    }

    def find_frontend_file(req_path):
        if not req_path:
            return frontend_dir / "index.html" if (frontend_dir / "index.html").is_file() else None

        clean = req_path.strip("/").replace("\\", "/")
        while clean.startswith("../"):
            clean = clean[3:].strip("/")

        # Never serve API endpoints as static files
        if clean.startswith("api/"):
            return None

        # 1. Exact file match in frontend_dir (e.g. css/style.css, js/auth.js, index.html)
        candidate = frontend_dir / clean
        if candidate.is_file():
            return candidate

        # 2. Check friendly routes mapping (clean and clean without .html)
        norm = clean.lower()
        norm_no_ext = norm.removesuffix(".html")
        if norm_no_ext in FRIENDLY_ROUTES:
            candidate = frontend_dir / FRIENDLY_ROUTES[norm_no_ext]
            if candidate.is_file():
                return candidate

        # 3. Check directly in frontend/pages/
        candidate = frontend_dir / "pages" / clean
        if candidate.is_file():
            return candidate
        if (frontend_dir / "pages" / f"{clean}.html").is_file():
            return frontend_dir / "pages" / f"{clean}.html"

        # 4. Handle "pages/", "auth/", "pages/auth/" prefixes
        for prefix in ["pages/", "auth/", "pages/auth/"]:
            if clean.startswith(prefix):
                sub = clean.removeprefix(prefix)
                if (frontend_dir / "pages" / sub).is_file():
                    return frontend_dir / "pages" / sub
                if (frontend_dir / "pages" / f"{sub}.html").is_file():
                    return frontend_dir / "pages" / f"{sub}.html"

        # 5. Check subdirectories under pages/ (student/, recruiter/, admin/, industry/)
        for subfolder in ["student", "recruiter", "admin", "industry"]:
            if clean.startswith(f"{subfolder}/"):
                sub = clean.removeprefix(f"{subfolder}/")
                if (frontend_dir / "pages" / subfolder / sub).is_file():
                    return frontend_dir / "pages" / subfolder / sub
                if (frontend_dir / "pages" / subfolder / f"{sub}.html").is_file():
                    return frontend_dir / "pages" / subfolder / f"{sub}.html"
            # Also check direct file inside subfolder
            if (frontend_dir / "pages" / subfolder / clean).is_file():
                return frontend_dir / "pages" / subfolder / clean
            if (frontend_dir / "pages" / subfolder / f"{clean}.html").is_file():
                return frontend_dir / "pages" / subfolder / f"{clean}.html"

        # 6. Check frontend_dir / clean.html
        if (frontend_dir / f"{clean}.html").is_file():
            return frontend_dir / f"{clean}.html"

        # 7. Check directory with index.html
        if (candidate / "index.html").is_file():
            return candidate / "index.html"

        return None

    # Dedicated top-level routes for primary application views
    @app.route("/login", methods=["GET"])
    @app.route("/login.html", methods=["GET"])
    @app.route("/pages/login.html", methods=["GET"])
    def login_view():
        return send_from_directory(frontend_dir / "pages", "login.html")

    @app.route("/register", methods=["GET"])
    @app.route("/register.html", methods=["GET"])
    @app.route("/pages/register.html", methods=["GET"])
    def register_view():
        return send_from_directory(frontend_dir / "pages", "register.html")

    @app.route("/recruiter", methods=["GET"])
    @app.route("/recruiter/jobs", methods=["GET"])
    @app.route("/recruiter/jobs.html", methods=["GET"])
    @app.route("/pages/recruiter/jobs.html", methods=["GET"])
    @app.route("/industry", methods=["GET"])
    @app.route("/industry/jobs", methods=["GET"])
    @app.route("/industry/jobs.html", methods=["GET"])
    @app.route("/pages/industry/jobs.html", methods=["GET"])
    def recruiter_jobs_view():
        return send_from_directory(frontend_dir / "pages" / "recruiter", "jobs.html")

    @app.route("/admin", methods=["GET"])
    @app.route("/admin/dashboard", methods=["GET"])
    @app.route("/admin/dashboard.html", methods=["GET"])
    @app.route("/pages/admin/dashboard.html", methods=["GET"])
    def admin_dashboard_view():
        return send_from_directory(frontend_dir / "pages" / "admin", "dashboard.html")

    @app.route("/admin/jobs", methods=["GET"])
    @app.route("/admin/jobs.html", methods=["GET"])
    @app.route("/pages/admin/jobs.html", methods=["GET"])
    def admin_jobs_view():
        return send_from_directory(frontend_dir / "pages" / "admin", "jobs.html")

    @app.route("/student/dashboard", methods=["GET"])
    @app.route("/student/dashboard.html", methods=["GET"])
    @app.route("/dashboard", methods=["GET"])
    @app.route("/dashboard.html", methods=["GET"])
    @app.route("/pages/student/dashboard.html", methods=["GET"])
    def student_dashboard_view():
        return send_from_directory(frontend_dir / "pages" / "student", "dashboard.html")

    @app.route("/student/jobs", methods=["GET"])
    @app.route("/student/jobs.html", methods=["GET"])
    @app.route("/jobs", methods=["GET"])
    @app.route("/jobs.html", methods=["GET"])
    @app.route("/pages/student/jobs.html", methods=["GET"])
    def student_jobs_view():
        return send_from_directory(frontend_dir / "pages" / "student", "jobs.html")

    @app.route("/student/applications", methods=["GET"])
    @app.route("/student/applications.html", methods=["GET"])
    @app.route("/applications", methods=["GET"])
    @app.route("/applications.html", methods=["GET"])
    @app.route("/pages/student/applications.html", methods=["GET"])
    def student_applications_view():
        return send_from_directory(frontend_dir / "pages" / "student", "applications.html")

    @app.route("/student/resume", methods=["GET"])
    @app.route("/student/resume-analysis", methods=["GET"])
    @app.route("/student/resume-analysis.html", methods=["GET"])
    @app.route("/resume", methods=["GET"])
    @app.route("/resume-analysis", methods=["GET"])
    @app.route("/pages/student/resume-analysis.html", methods=["GET"])
    def student_resume_view():
        return send_from_directory(frontend_dir / "pages" / "student", "resume-analysis.html")

    @app.route("/why-not-selected", methods=["GET"])
    @app.route("/placement-intelligence", methods=["GET"])
    @app.route("/student/why-not-selected", methods=["GET"])
    @app.route("/pages/student/why-not-selected", methods=["GET"])
    @app.route("/pages/student/why-not-selected.html", methods=["GET"])
    def why_not_selected_view():
        return send_from_directory(frontend_dir / "pages" / "student", "why-not-selected.html")

    @app.route("/alumni", methods=["GET"])
    @app.route("/alumni-network", methods=["GET"])
    @app.route("/student/alumni", methods=["GET"])
    @app.route("/pages/student/alumni", methods=["GET"])
    @app.route("/pages/student/alumni.html", methods=["GET"])
    def alumni_view():
        return send_from_directory(frontend_dir / "pages" / "student", "alumni.html")

    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def serve_frontend(path):
        from flask import request
        if request.method != "GET":
            if path.startswith("industry/") or path.startswith("students/") or path.startswith("admin/"):
                return error_response(message=f"API endpoints must start with /api/ (e.g. /api/{path})", status_code=404)
            return error_response(message="Method Not Allowed", status_code=405)

        found_file = find_frontend_file(path)
        if found_file and found_file.is_file():
            return send_from_directory(found_file.parent, found_file.name)

        return error_response(message="Resource Not Found", status_code=404)

    # Wrap Flask's default static handler to automatically resolve extensionless .html files and friendly routes
    def custom_static_view(filename=None, **kwargs):
        from flask import abort
        if not filename and "filename" in kwargs:
            filename = kwargs["filename"]
        if not filename:
            abort(404)

        found_file = find_frontend_file(filename)
        if found_file and found_file.is_file():
            return send_from_directory(found_file.parent, found_file.name)

        abort(404)

    app.view_functions["static"] = custom_static_view

    # Register global JSON error handlers
    register_error_handlers(app)

    # Automatically ensure database tables and foundational demo users exist
    _ensure_demo_users_auto_seed(app)

    return app


def _ensure_demo_users_auto_seed(app):
    """
    Ensures all database tables exist, syncs any missing model columns,
    and seeds foundational demonstration accounts (admin, recruiter, student)
    automatically so users can sign in immediately without manual terminal commands.
    """
    with app.app_context():
        try:
            from backend.models.user import User
            admin_user = User.query.filter_by(email="admin@college.edu").first()
            recruiter_user = User.query.filter_by(email="recruiter@company.com").first()
            student_user = User.query.filter_by(email="rahul@college.edu").first()

            if not (admin_user and recruiter_user and student_user):
                from backend.schema_sync import sync_missing_columns
                sync_missing_columns()
                from backend.seed_sih_demo import seed_database
                seed_database(app)
        except Exception as exc:
            app.logger.info(f"Auto demo seeding note: {exc}")


def register_error_handlers(app):
    """
    Registers standardized JSON error handlers for common HTTP status codes.
    """
    @app.errorhandler(400)
    def bad_request_error(error):
        return error_response(message="Bad Request", status_code=400, error_details=str(error))

    @app.errorhandler(404)
    def not_found_error(error):
        return error_response(message="Resource Not Found", status_code=404)

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return error_response(message="Method Not Allowed", status_code=405)

    @app.errorhandler(500)
    def internal_server_error(error):
        return error_response(
            message="Internal Server Error. Please contact support or check server logs.",
            status_code=500
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return error_response(
            message=error.description,
            status_code=error.code
        )

    from sqlalchemy.exc import OperationalError, SQLAlchemyError

    @app.errorhandler(OperationalError)
    def handle_db_operational_error(error):
        return error_response(
            message="MySQL connection unavailable. Check the database connection settings and confirm the server is accepting connections.",
            status_code=503,
            error_details=str(error.orig) if hasattr(error, 'orig') else str(error)
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_db_general_error(error):
        return error_response(
            message="A database error occurred while processing your request.",
            status_code=500,
            error_details=str(error)
        )


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")
    debug = app.config.get("DEBUG", True)
    
    print(f"Starting server on http://{host}:{port} (Debug: {debug})...")
    app.run(host=host, port=port, debug=debug)

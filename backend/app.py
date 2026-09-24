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
        "admin": "pages/admin/dashboard.html",
        "admin/dashboard": "pages/admin/dashboard.html",
        "industry": "pages/industry/jobs.html",
        "industry/dashboard": "pages/industry/jobs.html"
    }

    @app.route("/why-not-selected", methods=["GET"])
    @app.route("/placement-intelligence", methods=["GET"])
    @app.route("/student/why-not-selected", methods=["GET"])
    @app.route("/pages/student/why-not-selected", methods=["GET"])
    def why_not_selected_view():
        return send_from_directory(frontend_dir / "pages" / "student", "why-not-selected.html")

    @app.route("/alumni", methods=["GET"])
    @app.route("/alumni-network", methods=["GET"])
    @app.route("/student/alumni", methods=["GET"])
    @app.route("/pages/student/alumni", methods=["GET"])
    def alumni_view():
        return send_from_directory(frontend_dir / "pages" / "student", "alumni.html")

    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def serve_frontend(path):
        from flask import request
        if request.method != "GET":
            if path.startswith("industry/") or path.startswith("students/") or path.startswith("admin/"):
                return error_response(message=f"API endpoints must start with /api/ (e.g. /api/{path})", status_code=404)
            return error_response(message="Method Not Allowed", status_code=405)
        if path.startswith("api/"):
            return error_response(message="Resource Not Found", status_code=404)

        clean_path = path.strip("/").lower()
        if clean_path in FRIENDLY_ROUTES:
            rel_target = FRIENDLY_ROUTES[clean_path]
            if (frontend_dir / rel_target).exists():
                return send_from_directory(frontend_dir, rel_target)

        # 1. Exact file match
        target = frontend_dir / path
        if target.exists() and not target.is_dir():
            return send_from_directory(frontend_dir, path)

        # 2. Directory with index.html
        if (target / "index.html").exists():
            return send_from_directory(target, "index.html")

        # 3. Path with .html extension added (e.g. /pages/student/alumni -> alumni.html)
        target_html = frontend_dir / f"{path}.html"
        if target_html.exists() and not target_html.is_dir():
            return send_from_directory(frontend_dir, f"{path}.html")

        # 4. Resolve student page paths from clean URLs as well as /pages/student/.
        # Relative links such as alumni.html from /student/dashboard otherwise
        # resolve to /student/alumni.html and miss the actual frontend file.
        student_path = path.removeprefix("student/") if path.startswith("student/") else path
        student_target = frontend_dir / "pages" / "student" / student_path
        if student_target.exists() and not student_target.is_dir():
            return send_from_directory(frontend_dir / "pages" / "student", student_path)

        student_target_html = frontend_dir / "pages" / "student" / f"{student_path}.html"
        if student_target_html.exists() and not student_target_html.is_dir():
            return send_from_directory(frontend_dir / "pages" / "student", f"{student_path}.html")

        return error_response(message="Resource Not Found", status_code=404)

    # Wrap Flask's default static handler to automatically resolve extensionless .html files and friendly routes
    def custom_static_view(filename=None, **kwargs):
        from flask import abort
        if not filename and "filename" in kwargs:
            filename = kwargs["filename"]
        if not filename:
            abort(404)

        target = frontend_dir / filename
        if target.exists() and not target.is_dir():
            return send_from_directory(frontend_dir, filename)
        if (frontend_dir / f"{filename}.html").exists():
            return send_from_directory(frontend_dir, f"{filename}.html")
        if (target / "index.html").exists():
            return send_from_directory(target, "index.html")

        clean_name = filename.strip("/").lower()
        if clean_name in FRIENDLY_ROUTES:
            rel = FRIENDLY_ROUTES[clean_name]
            if (frontend_dir / rel).exists():
                return send_from_directory(frontend_dir, rel)

        # Flask's static route takes precedence for paths ending in .html, so
        # resolve clean student URLs here as well as in the catch-all route.
        student_filename = filename.removeprefix("student/") if filename.startswith("student/") else filename
        student_file = frontend_dir / "pages" / "student" / student_filename
        if student_file.exists() and not student_file.is_dir():
            return send_from_directory(frontend_dir / "pages" / "student", student_filename)

        if (frontend_dir / "pages" / "student" / f"{student_filename}.html").exists():
            return send_from_directory(frontend_dir / "pages" / "student", f"{student_filename}.html")

        abort(404)

    app.view_functions["static"] = custom_static_view

    # Register global JSON error handlers
    register_error_handlers(app)

    return app


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

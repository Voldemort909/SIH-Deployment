"""
JWT token management and Role-Based Access Control (RBAC) authorization decorators.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import request, current_app

from backend.extensions import db
from backend.models.user import User
from backend.utils.response import error_response


def generate_token(user, expires_in_hours=24):
    """
    Generates a stateless HS256 signed JWT token for an authenticated user.
    """
    secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.lower(),
        "iat": now,
        "exp": now + timedelta(hours=expires_in_hours)
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token):
    """
    Decodes and validates a JWT token.
    Returns payload dictionary or raises jwt exceptions.
    """
    secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key")
    return jwt.decode(token, secret_key, algorithms=["HS256"])


def get_token_from_header():
    """
    Extracts Bearer token from the HTTP Authorization header or query param.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    
    query_token = request.args.get("token")
    if query_token:
        return query_token

    return None


def token_required(fn):
    """
    Decorator requiring a valid JWT Bearer token.
    Injects `current_user` into `request.current_user` and passes it as first argument if accepted.
    """
    @wraps(fn)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return error_response(
                message="Authentication token is missing. Please provide a valid Bearer token.",
                status_code=401
            )

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return error_response(
                message="Authentication token has expired. Please log in again.",
                status_code=401
            )
        except jwt.InvalidTokenError:
            return error_response(
                message="Invalid authentication token.",
                status_code=401
            )

        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return error_response("Invalid token subject.", 401)

        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            return error_response(
                message="User account is invalid or deactivated.",
                status_code=401
            )

        # Store authenticated user in request context
        request.current_user = user

        # Support view functions that accept current_user argument
        import inspect
        sig = inspect.signature(fn)
        if "current_user" in sig.parameters:
            kwargs["current_user"] = user

        return fn(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """
    Decorator enforcing role-based access control.
    Requires valid token and checks user.role against allowed_roles.
    Also validates that industry_expert accounts are APPROVED before accessing industry endpoints.
    """
    normalized_allowed = [r.lower() for r in allowed_roles]

    def decorator(fn):
        @wraps(fn)
        @token_required
        def decorated(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return error_response("Authentication required.", 401)

            user_role = user.role.lower()

            # Check role permission
            if user_role not in normalized_allowed:
                return error_response(
                    message=f"Access forbidden: This action requires {', '.join(allowed_roles)} privileges.",
                    status_code=403
                )

            # Industry approval verification: PENDING industry accounts cannot access industry-only resources
            if user_role == "industry_expert" and "industry_expert" in normalized_allowed:
                expert_profile = user.expert_profile
                if expert_profile and expert_profile.status.upper() != "APPROVED":
                    return error_response(
                        message="Access forbidden: Your industry account is currently PENDING administrator approval.",
                        status_code=403,
                        error_details={"approval_status": expert_profile.status.upper()}
                    )

            import inspect
            sig = inspect.signature(fn)
            if "current_user" in sig.parameters and "current_user" not in kwargs:
                kwargs["current_user"] = user

            return fn(*args, **kwargs)

        return decorated

    return decorator


# Convenient role-specific decorators
def student_required(fn):
    """Restricts route access exclusively to authenticated students."""
    return role_required("student")(fn)


def industry_required(fn):
    """Restricts route access exclusively to approved industry experts / recruiters."""
    return role_required("industry_expert")(fn)


def admin_required(fn):
    """Restricts route access exclusively to college placement cell administrators."""
    return role_required("admin")(fn)

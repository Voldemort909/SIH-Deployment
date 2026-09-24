"""
Input validation utilities for user registration, authentication, and data hygiene.
"""
import re


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email):
    """Checks if email string is non-empty and matches standard format."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_password(password, min_length=6):
    """Validates password length and type."""
    if not password or not isinstance(password, str):
        return False, "Password is required."
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    return True, None


def split_full_name(name):
    """Utility to split a single full name string into first_name and last_name."""
    if not name or not isinstance(name, str):
        return "", ""
    parts = name.strip().split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name


def validate_student_registration(data):
    """
    Validates input payload for student registration.
    Returns: (is_valid, error_message, cleaned_data)
    """
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object.", None

    # Handle name fields (supports both 'name' or 'first_name'/'last_name')
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    if not first_name and "name" in data:
        first_name, last_name = split_full_name(data.get("name"))

    if not first_name:
        return False, "Student name (or first_name) is required.", None

    roll_number = str(data.get("roll_number") or data.get("enrollment_number") or "").strip()
    if not roll_number:
        return False, "Enrollment / Roll number is required.", None

    email = str(data.get("email") or "").strip().lower()
    if not validate_email(email):
        return False, "A valid college email address is required.", None

    password = data.get("password")
    is_pwd_valid, pwd_err = validate_password(password)
    if not is_pwd_valid:
        return False, pwd_err, None

    department = str(data.get("department") or data.get("branch") or "").strip()
    if not department:
        return False, "Branch / Department is required.", None

    degree = str(data.get("degree") or "B.Tech").strip()

    try:
        batch_year = int(data.get("batch_year") or data.get("graduation_year") or 0)
        if batch_year < 1990 or batch_year > 2040:
            return False, "Graduation year must be a valid 4-digit year (e.g. 2026).", None
    except (ValueError, TypeError):
        return False, "Graduation year must be a valid integer.", None

    cgpa = data.get("cgpa")
    if cgpa is not None and cgpa != "":
        try:
            cgpa_val = float(cgpa)
            if cgpa_val < 0.0 or cgpa_val > 10.0:
                return False, "CGPA must be between 0.0 and 10.0.", None
        except (ValueError, TypeError):
            return False, "CGPA must be a valid numeric value.", None
    else:
        cgpa_val = None

    cleaned = {
        "first_name": first_name,
        "last_name": last_name,
        "roll_number": roll_number,
        "email": email,
        "password": password,
        "department": department,
        "degree": degree,
        "batch_year": batch_year,
        "cgpa": cgpa_val,
        "phone": str(data.get("phone") or "").strip() or None,
        "gender": str(data.get("gender") or "").strip() or None,
    }
    return True, None, cleaned


def validate_industry_registration(data):
    """
    Validates input payload for industry expert registration.
    Returns: (is_valid, error_message, cleaned_data)
    """
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object.", None

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    if not first_name and "name" in data:
        first_name, last_name = split_full_name(data.get("name"))

    if not first_name:
        return False, "Name (or first_name) is required.", None

    email = str(data.get("email") or "").strip().lower()
    if not validate_email(email):
        return False, "A valid corporate email address is required.", None

    password = data.get("password")
    is_pwd_valid, pwd_err = validate_password(password)
    if not is_pwd_valid:
        return False, pwd_err, None

    designation = str(data.get("designation") or "").strip()
    if not designation:
        return False, "Designation / Role is required.", None

    company_name = str(data.get("company") or data.get("company_name") or "").strip()
    if not company_name:
        return False, "Company name is required.", None

    experience_years = data.get("experience_years")
    if experience_years is not None and experience_years != "":
        try:
            exp_val = int(experience_years)
            if exp_val < 0 or exp_val > 70:
                return False, "Experience years must be a valid positive number.", None
        except (ValueError, TypeError):
            return False, "Experience years must be an integer.", None
    else:
        exp_val = 0

    cleaned = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "designation": designation,
        "company_name": company_name,
        "experience_years": exp_val,
        "linkedin_url": str(data.get("linkedin_url") or "").strip() or None,
    }
    return True, None, cleaned


def validate_login(data):
    """Validates login payload."""
    if not data or not isinstance(data, dict):
        return False, "Request body must be a JSON object.", None

    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not email:
        return False, "Email is required.", None
    if not password:
        return False, "Password is required.", None

    return True, None, {"email": email, "password": password}

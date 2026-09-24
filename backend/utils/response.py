"""
Standardized JSON API response helpers for the Flask backend.
Ensures uniform response structures across all endpoints and error handlers.
"""
from flask import jsonify


def api_response(message="Success", data=None, status_code=200, **kwargs):
    """
    Standard successful or operational JSON response.
    """
    payload = {
        "status": "success",
        "message": message,
    }
    if data is not None:
        payload["data"] = data
        
    for key, value in kwargs.items():
        payload[key] = value

    return jsonify(payload), status_code


def error_response(message="An error occurred", status_code=400, error_details=None):
    """
    Standard error JSON response.
    """
    payload = {
        "status": "error",
        "message": message,
    }
    if error_details is not None:
        payload["error"] = error_details

    return jsonify(payload), status_code

"""Consistent error envelope for every API error.

{"error": {"code": "validation_error", "message": "...", "details": {...}}}
"""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

_STATUS_CODES = {
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # unhandled -> Django's 500 handling

    if isinstance(exc, ValidationError):
        code, message, details = "validation_error", "Invalid input.", response.data
    else:
        data = response.data if isinstance(response.data, dict) else {}
        code = (
            data.get("code")  # e.g. Simple JWT's "token_not_valid"
            or getattr(getattr(exc, "detail", None), "code", None)
            or _STATUS_CODES.get(response.status_code)
            or "error"
        )
        message = str(data.get("detail", "Request failed."))
        details = None

    response.data = {"error": {"code": str(code), "message": message, "details": details}}
    return response

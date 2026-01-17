from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def _error_type(status_code: int, detail) -> str:
    if status_code == status.HTTP_400_BAD_REQUEST and isinstance(detail, (dict, list)):
        return "validation_error"
    if status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        return "auth_error"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    return "api_error"


def core_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    request = context.get("request")
    request_data = None
    if request is not None and hasattr(request, "data"):
        try:
            request_data = dict(request.data)
        except Exception:
            request_data = request.data

    if isinstance(exc, ValidationError):
        message = "Validation failed"
    else:
        message = detail.get("detail") if isinstance(detail, dict) else "Request failed"

    payload = {
        "error": {
            "type": _error_type(response.status_code, detail),
            "message": message,
            "details": detail,
        }
    }
    if request_data is not None:
        payload["data"] = request_data
    response.data = payload
    return response

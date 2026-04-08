import logging
from collections.abc import Mapping

from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.app_server.responses.api_responses import (
    error_envelope_response,
    warning_envelope_response,
)

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {
    'password',
    'confirm_password',
    'old_password',
    'new_password',
    'current_password',
    'access',
    'refresh',
    'token',
    'authorization',
}


def _to_list(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _normalize_error_details(details):
    if details is None:
        return {}

    if isinstance(details, list):
        return {'non_field_errors': [str(item) for item in details]}

    if isinstance(details, str):
        return {'non_field_errors': [details]}

    if isinstance(details, Mapping):
        normalized = {}
        for field, value in details.items():
            normalized[field] = _to_list(value)
        return normalized

    return {'non_field_errors': [str(details)]}


def _errors_to_single_string_map(error_dict):
    """Map field -> first message string for code 603."""
    if not error_dict:
        return {}
    out = {}
    for field, messages in error_dict.items():
        if messages:
            out[field] = str(messages[0])
        else:
            out[field] = ''
    return out


def _extract_message(error_dict, fallback_message='Request failed.'):
    if not error_dict:
        return fallback_message

    for messages in error_dict.values():
        if messages:
            return str(messages[0])

    return fallback_message


def _sanitize_old_data(data):
    if not isinstance(data, Mapping):
        return {}

    sanitized = {}
    for key, value in data.items():
        if str(key).lower() in SENSITIVE_FIELDS:
            continue

        if isinstance(value, list):
            sanitized[key] = [str(item) for item in value]
            continue

        if hasattr(value, 'name'):
            sanitized[key] = str(value.name)
            continue

        sanitized[key] = value

    return sanitized


def _get_old_data_from_request(request):
    if request is None:
        return {}

    request_data = getattr(request, 'data', None)
    if request_data is None:
        return {}

    if hasattr(request_data, 'dict'):
        return _sanitize_old_data(request_data.dict())

    if isinstance(request_data, Mapping):
        return _sanitize_old_data(dict(request_data))

    return {}


def error_response(request, message, status_code, error=None):
    """
    Backwards-compatible name for views: maps HTTP semantics to numeric codes.
    When ``error`` is provided, returns 603 with ``old_data`` and string ``errors`` per field.
    """
    error_payload = _normalize_error_details(error)

    if error_payload:
        old_data = _get_old_data_from_request(request)
        string_errors = _errors_to_single_string_map(error_payload)
        return warning_envelope_response(
            code=603,
            message=message,
            data={
                'old_data': old_data,
                'errors': string_errors,
            },
            http_status=status_code,
        )

    if status_code == status.HTTP_401_UNAUTHORIZED:
        return error_envelope_response(
            code=601,
            message=message,
            data=None,
            http_status=status_code,
        )
    if status_code == status.HTTP_403_FORBIDDEN:
        return error_envelope_response(
            code=602,
            message=message,
            data=None,
            http_status=status_code,
        )

    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return error_envelope_response(
            code=600,
            message=message,
            data=None,
            http_status=status_code,
        )

    return warning_envelope_response(
        code=604,
        message=message,
        data=None,
        http_status=status_code,
    )


def custom_exception_handler(exc, context):
    request = context.get('request')

    if isinstance(exc, Http404):
        return warning_envelope_response(
            code=604,
            message='Không tìm thấy tài nguyên.',
            data=None,
            http_status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, DjangoPermissionDenied):
        return error_envelope_response(
            code=602,
            message='Bạn không có quyền thực hiện thao tác này.',
            data=None,
            http_status=status.HTTP_403_FORBIDDEN,
        )

    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception('Unhandled exception: %s', exc)
        return error_envelope_response(
            code=600,
            message='Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.',
            data=None,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        error_payload = _normalize_error_details(response.data)
        message = _extract_message(error_payload, fallback_message=str(exc))
        return error_envelope_response(
            code=601,
            message=message,
            data=None,
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, PermissionDenied):
        error_payload = _normalize_error_details(response.data)
        message = _extract_message(error_payload, fallback_message=str(exc))
        return error_envelope_response(
            code=602,
            message=message,
            data=None,
            http_status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, NotFound):
        error_payload = _normalize_error_details(response.data)
        message = _extract_message(error_payload, fallback_message='Không tìm thấy tài nguyên.')
        return warning_envelope_response(
            code=604,
            message=message,
            data=None,
            http_status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, ValidationError):
        error_payload = _normalize_error_details(response.data)
        message = _extract_message(error_payload, fallback_message='Dữ liệu không hợp lệ.')
        string_errors = _errors_to_single_string_map(error_payload)
        return warning_envelope_response(
            code=603,
            message=message,
            data={
                'old_data': _get_old_data_from_request(request),
                'errors': string_errors,
            },
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    status_code = response.status_code
    error_payload = _normalize_error_details(response.data)
    message = _extract_message(error_payload, fallback_message=str(exc))

    if status_code == status.HTTP_400_BAD_REQUEST:
        if isinstance(response.data, dict) and response.data:
            string_errors = _errors_to_single_string_map(error_payload)
            if string_errors:
                return warning_envelope_response(
                    code=603,
                    message=message,
                    data={
                        'old_data': _get_old_data_from_request(request),
                        'errors': string_errors,
                    },
                    http_status=status_code,
                )
        return warning_envelope_response(
            code=604,
            message=message,
            data=None,
            http_status=status_code,
        )

    if status_code == status.HTTP_401_UNAUTHORIZED:
        return error_envelope_response(
            code=601,
            message=message,
            data=None,
            http_status=status_code,
        )

    if status_code == status.HTTP_403_FORBIDDEN:
        return error_envelope_response(
            code=602,
            message=message,
            data=None,
            http_status=status_code,
        )

    if status_code == status.HTTP_404_NOT_FOUND:
        return warning_envelope_response(
            code=604,
            message=message,
            data=None,
            http_status=status_code,
        )

    if status_code >= 500:
        return error_envelope_response(
            code=600,
            message='Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.',
            data=None,
            http_status=status_code,
        )

    if status_code >= 400:
        return warning_envelope_response(
            code=604,
            message=message,
            data=None,
            http_status=status_code,
        )

    return response

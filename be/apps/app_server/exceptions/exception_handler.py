from collections.abc import Mapping

from rest_framework.response import Response
from rest_framework.views import exception_handler


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
    error_payload = _normalize_error_details(error)
    if not error_payload:
        error_payload = {'non_field_errors': [message]}

    return Response(
        {
            'message': message,
            'old_data': _get_old_data_from_request(request),
            'error': error_payload,
        },
        status=status_code,
    )


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    request = context.get('request')
    error_payload = _normalize_error_details(response.data)
    message = _extract_message(error_payload, fallback_message=str(exc))

    response.data = {
        'message': message,
        'old_data': _get_old_data_from_request(request),
        'error': error_payload,
    }
    return response

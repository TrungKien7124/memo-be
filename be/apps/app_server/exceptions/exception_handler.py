from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_type = exc.__class__.__name__
        error_data = {
            'error': {
                'type': error_type,
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                'details': response.data if isinstance(response.data, dict) else {'errors': response.data},
            },
            'data': None,
        }
        response.data = error_data

    return response

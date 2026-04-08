from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message='Thành công.', http_status=status.HTTP_200_OK):
    return Response(
        {
            'status': 'success',
            'code': 200,
            'message': message,
            'data': data,
        },
        status=http_status,
    )


def paginated_success_response(records, pageinfo, message='Lấy dữ liệu thành công.'):
    return Response(
        {
            'status': 'success',
            'code': 200,
            'message': message,
            'data': {
                'records': records,
                'pageinfo': pageinfo,
            },
        },
        status=status.HTTP_200_OK,
    )


def warning_envelope_response(code, message, data=None, http_status=status.HTTP_400_BAD_REQUEST):
    assert code in (603, 604)
    return Response(
        {
            'status': 'warning',
            'code': code,
            'message': message,
            'data': data,
        },
        status=http_status,
    )


def error_envelope_response(code, message, data=None, http_status=status.HTTP_500_INTERNAL_SERVER_ERROR):
    assert code in (600, 601, 602)
    return Response(
        {
            'status': 'error',
            'code': code,
            'message': message,
            'data': data,
        },
        status=http_status,
    )

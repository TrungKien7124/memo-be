from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.app_server.models.user_profile_model import UserProfile
from apps.app_server.responses.api_responses import success_response
from apps.app_server.serializers.auth_serializer import (
    RegisterSerializer,
    LoginSerializer,
    get_tokens_for_user,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.create(user=user, display_name=user.username)
        tokens = get_tokens_for_user(user)
        return success_response(
            data={
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                },
                'tokens': tokens,
            },
            message='Đăng ký thành công.',
            http_status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        return success_response(
            data={
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                },
                'tokens': tokens,
            },
            message='Đăng nhập thành công.',
        )


class CustomTokenRefreshView(TokenRefreshView):
    """Wraps DRF-simplejwt refresh in standard response format."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            inner = response.data if isinstance(response.data, dict) else {}
            response.data = {
                'status': 'success',
                'code': 200,
                'message': 'Làm mới token thành công.',
                'data': inner,
            }
        return response

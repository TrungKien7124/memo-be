from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.app_server.models.user_profile_model import UserProfile
from apps.app_server.responses.api_responses import success_response
from apps.app_server.serializers.user_profile_serializer import UserProfileSerializer


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return success_response(
            data=serializer.data,
            message='Lấy hồ sơ thành công.',
        )

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Cập nhật hồ sơ thành công.',
        )

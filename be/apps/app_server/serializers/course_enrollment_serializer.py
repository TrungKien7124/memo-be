from rest_framework import serializers

from apps.app_server.models.course_enrollment_model import CourseEnrollment


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    granted_by_id = serializers.UUIDField(source='granted_by.id', read_only=True, allow_null=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            'id',
            'course',
            'user_id',
            'email',
            'username',
            'role',
            'enrolled_at',
            'source',
            'granted_by_id',
        ]

from rest_framework import serializers

from apps.app_server.models.lesson_comment_model import LessonComment
from apps.app_server.services.course_access_service import is_admin_user


class LessonCommentSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    def validate_content(self, value):
        if not isinstance(value, str) or not value.strip():
            raise serializers.ValidationError('Comment content must not be blank.')
        return value.strip()

    def validate(self, attrs):
        lesson = attrs.get('lesson') or getattr(self.instance, 'lesson', None)
        parent = attrs.get('parent') if 'parent' in attrs else getattr(self.instance, 'parent', None)
        if parent and lesson and parent.lesson_id != lesson.id:
            raise serializers.ValidationError(
                {'parent': ['Parent comment must belong to the same lesson.']}
            )
        return attrs

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        if obj.is_deleted:
            return False
        if is_admin_user(request.user):
            return True
        return obj.user_id == request.user.id

    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        if obj.is_deleted:
            return False
        if is_admin_user(request.user):
            return True
        return obj.user_id == request.user.id

    def to_representation(self, instance):
        payload = super().to_representation(instance)
        payload['is_deleted'] = bool(instance.is_deleted)
        # Normalize parent to string UUID for API clients and tests.
        parent_id = payload.get('parent')
        if parent_id is not None:
            payload['parent'] = str(parent_id)
        if instance.is_deleted:
            payload['content'] = '[deleted]'
        return payload

    class Meta:
        model = LessonComment
        fields = [
            'id',
            'lesson',
            'parent',
            'content',
            'is_deleted',
            'edited_at',
            'created_at',
            'updated_at',
            'user_id',
            'user_email',
            'user_username',
            'user_role',
            'can_edit',
            'can_delete',
        ]
        read_only_fields = [
            'id',
            'is_deleted',
            'edited_at',
            'created_at',
            'updated_at',
            'user_id',
            'user_email',
            'user_username',
            'user_role',
            'can_edit',
            'can_delete',
        ]

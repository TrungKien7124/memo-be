from rest_framework.permissions import BasePermission

from apps.app_server.models.user_model import ROLE_ADMIN, ROLE_TEACHER


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == ROLE_ADMIN


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (ROLE_TEACHER, ROLE_ADMIN)
        )


class IsOwner(BasePermission):
    """Object-level permission: only the owner can access."""

    owner_field = 'user'

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, self.owner_field, None)
        if owner is None:
            return False
        owner_id = owner.id if hasattr(owner, 'id') else owner
        return request.user.id == owner_id


class IsOwnerOrAdmin(BasePermission):
    owner_field = 'user'

    def has_object_permission(self, request, view, obj):
        if request.user.role == ROLE_ADMIN:
            return True
        owner = getattr(obj, self.owner_field, None)
        if owner is None:
            return False
        owner_id = owner.id if hasattr(owner, 'id') else owner
        return request.user.id == owner_id

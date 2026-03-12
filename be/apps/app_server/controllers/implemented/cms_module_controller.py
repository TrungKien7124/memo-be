from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.serializers.implemented.cms_module_serializer import ModuleSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin


class ModuleViewSet(CoreModelViewSet):
    serializer_class = ModuleSerializer
    filterset_fields = ['course']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Module.objects.select_related('course').all()

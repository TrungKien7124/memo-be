from rest_framework import status, viewsets

from apps.app_server.responses.api_responses import success_response


class CoreModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet providing standard CRUD with soft-delete support
    and consistent response format.
    """

    normalizer_class = None

    def get_normalized_data(self):
        if self.normalizer_class is not None:
            normalizer = self.normalizer_class(self.request.data)
            return normalizer.normalize()
        return self.request.data

    def create(self, request, *args, **kwargs):
        data = self.get_normalized_data()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            data=serializer.data,
            message='Tạo thành công.',
            http_status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message='Lấy dữ liệu thành công.',
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = self.get_normalized_data()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(
            data=serializer.data,
            message='Cập nhật thành công.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if hasattr(instance, 'soft_delete'):
            instance.soft_delete()
        else:
            self.perform_destroy(instance)
        return success_response(
            data=None,
            message='Xóa thành công.',
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message='Lấy dữ liệu thành công.',
        )

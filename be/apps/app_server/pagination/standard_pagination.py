from rest_framework.pagination import PageNumberPagination

from apps.app_server.responses.api_responses import paginated_success_response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        count = self.page.paginator.count
        current = self.page.number
        size = self.get_page_size(self.request) or 1
        total_pages = (count + size - 1) // size if count > 0 else 0
        pageinfo = {
            'count': count,
            'current': current,
            'total_pages': total_pages,
            'size': size,
        }
        return paginated_success_response(data, pageinfo)

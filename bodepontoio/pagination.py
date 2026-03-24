import math

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class BodePaginationMixin:
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["_paginated"] = True
        return response


class StandardPagination(BodePaginationMixin, PageNumberPagination):
    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        limit = self.get_page_size(self.request)
        total_pages = math.ceil(total / limit) if limit else 1

        return Response(
            {
                "items": data,
                "pagination": {
                    "page": self.page.number,
                    "limit": limit,
                    "total": total,
                    "totalPages": total_pages,
                    "hasNext": self.page.has_next(),
                    "hasPrev": self.page.has_previous(),
                },
                "_paginated": True,
            }
        )

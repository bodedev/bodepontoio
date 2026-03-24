from rest_framework.renderers import JSONRenderer


class SuccessJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")

        # Error responses are already formatted by the exception handler — pass through
        if response is not None and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        # Empty response (e.g. 204 No Content) → {"success": true} with 200
        if data is None:
            if response is not None:
                response.status_code = 200
            return super().render(
                {"success": True}, accepted_media_type, renderer_context
            )

        # Paginated response — marked by BodePaginationMixin or StandardPagination
        if isinstance(data, dict) and data.pop("_paginated", False):
            return super().render(
                {"success": True, "pagination": True, "data": data},
                accepted_media_type,
                renderer_context,
            )

        # Standard response
        return super().render(
            {"success": True, "pagination": False, "data": data},
            accepted_media_type,
            renderer_context,
        )

from .renderers import SuccessJSONRenderer


class BodepontoioMixin:
    """
    Opt-in mixin for views that should use bodepontoio's standard response format.

    Apply this mixin to any view that should:
    - Wrap success responses in ``{"success": true, "data": ...}``
    - Format error responses via ``exception_handler_v2``

    Usage with ``exception_handler_v2``::

        # settings.py
        REST_FRAMEWORK = {
            "EXCEPTION_HANDLER": "bodepontoio.exceptions.exception_handler_v2",
        }

        # views.py
        from bodepontoio.mixins import BodepontoioMixin

        class MyView(BodepontoioMixin, APIView):
            ...
    """

    renderer_classes = [SuccessJSONRenderer]
    bodepontoio_format = True

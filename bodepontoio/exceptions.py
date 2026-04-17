import re

from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

_TYPE_MAP = {
    exceptions.ValidationError: "validation_error",
    exceptions.AuthenticationFailed: "authentication_error",
    exceptions.NotAuthenticated: "authentication_error",
    exceptions.PermissionDenied: "permission_error",
    exceptions.NotFound: "not_found",
    exceptions.ParseError: "parse_error",
    exceptions.MethodNotAllowed: "method_not_allowed",
    exceptions.NotAcceptable: "not_acceptable",
    exceptions.UnsupportedMediaType: "unsupported_media_type",
    exceptions.Throttled: "throttled",
}


def _get_error_type(exc):
    for exc_class, type_str in _TYPE_MAP.items():
        if isinstance(exc, exc_class):
            return type_str
    # Fallback: convert class name to snake_case (e.g. MyCustomError → my_custom_error)
    return re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()


def _flatten_errors(data, field=""):
    """Recursively flatten DRF error dicts/lists into a flat list of {field, message} dicts."""
    errors = []
    if isinstance(data, dict):
        for key, value in data.items():
            nested_field = f"{field}.{key}" if field else key
            errors.extend(_flatten_errors(value, field=nested_field))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                errors.extend(_flatten_errors(item, field=field))
            else:
                errors.append({"field": field or "non_field_errors", "message": str(item)})
    else:
        errors.append({"field": field or "non_field_errors", "message": str(data)})
    return errors


def _format_response(exc, response):
    """Apply bodepontoio error formatting to a DRF response."""
    error_type = _get_error_type(exc)

    if isinstance(exc, exceptions.ValidationError):
        response.data = {
            "success": False,
            "type": error_type,
            "errors": _flatten_errors(response.data),
        }
    else:
        detail = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(response.data)
        response.data = {
            "success": False,
            "type": error_type,
            "error": str(detail),
        }

    return response


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    return _format_response(exc, response)


def exception_handler_v2(exc, context):
    """
    Opt-in version of ``exception_handler``.

    Only applies bodepontoio error formatting to views that have
    ``bodepontoio_format = True`` (e.g. via ``BodepontoioMixin``).
    All other views receive plain DRF error responses, making this
    safe to set globally on projects that are gradually adopting
    bodepontoio.
    """
    view = context.get("view")
    if not getattr(view, "bodepontoio_format", False):
        return drf_exception_handler(exc, context)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    return _format_response(exc, response)

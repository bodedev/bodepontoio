import json
import time

from django.http import RawPostDataException
from django.template.response import ContentNotRenderedError

from bodepontoio.conf import bodepontoio_settings

_DEBUG_MW = "bodepontoio.middleware.APICallbackDebugMiddleware"
_AUTH_MW = "django.contrib.auth.middleware.AuthenticationMiddleware"


def install_debug_middleware(middleware):
    """
    Auto-inserts APICallbackDebugMiddleware when API_DEBUG_LOGGER_ENABLED is True.

    Call at the end of your settings file (after local overrides are imported):

        from bodepontoio.middleware import install_debug_middleware
        MIDDLEWARE = install_debug_middleware(MIDDLEWARE)
    """
    if not bodepontoio_settings.API_DEBUG_LOGGER_ENABLED or _DEBUG_MW in middleware:
        return middleware
    middleware = list(middleware)
    if _AUTH_MW in middleware:
        middleware.insert(middleware.index(_AUTH_MW) + 1, _DEBUG_MW)
    else:
        middleware.append(_DEBUG_MW)
    return middleware


SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key"}


class APICallbackDebugMiddleware:
    """
    Logs API request/response details to terminal for local debugging.

    Enable via BODEPONTOIO settings:

        BODEPONTOIO = {
            "API_DEBUG_LOGGER_ENABLED": True,
            "API_DEBUG_LOGGER_PATH_PREFIX": "/api/",   # optional
            "API_DEBUG_LOGGER_MAX_BODY_CHARS": 6000,   # optional
        }

    Then add to MIDDLEWARE (or let the auto-insert snippet in settings handle it):

        "bodepontoio.middleware.APICallbackDebugMiddleware"
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_enabled() or not request.path.startswith(self._path_prefix()):
            return self.get_response(request)

        self._snapshot_request_body(request)

        start_time = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        try:
            self._print_debug_block(request, response, duration_ms)
        except Exception as exc:  # pragma: no cover - debug path must never break API flow
            print(f"[API DEBUG] Failed to print callback log: {exc}")
        return response

    @staticmethod
    def _is_enabled():
        return bool(bodepontoio_settings.API_DEBUG_LOGGER_ENABLED)

    @staticmethod
    def _path_prefix():
        return bodepontoio_settings.API_DEBUG_LOGGER_PATH_PREFIX

    @staticmethod
    def _max_body_chars():
        return int(bodepontoio_settings.API_DEBUG_LOGGER_MAX_BODY_CHARS)

    def _print_debug_block(self, request, response, duration_ms):
        max_chars = self._max_body_chars()
        request_headers = self._sanitize_headers(request.headers)
        request_body = self._request_payload(request, max_chars)
        response_body = self._response_payload(response, max_chars)
        user_repr = self._resolve_user(request)

        lines = [
            "\n" + "=" * 90,
            "[API DEBUG] CALLBACK",
            "-" * 90,
            f"REQUEST: {request.method} {request.get_full_path()}",
            f"USER: {user_repr}",
            f"REQUEST_HEADERS: {json.dumps(request_headers, ensure_ascii=True)}",
            f"REQUEST_PAYLOAD: {request_body}",
            f"RESPONSE_STATUS: {response.status_code}",
            f"RESPONSE_HEADERS: {json.dumps(dict(response.items()), ensure_ascii=True)}",
            f"RESPONSE_BODY: {response_body}",
            f"DURATION_MS: {duration_ms:.2f}",
            "=" * 90,
        ]
        print("\n".join(lines))

    @staticmethod
    def _resolve_user(request):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return "anonymous"
        identifier = getattr(user, "email", "") or getattr(user, "username", "") or str(user.pk)
        return f"{identifier} ({user.pk})"

    def _request_payload(self, request, max_chars):
        method = request.method.upper()
        if method in {"GET", "HEAD", "OPTIONS"}:
            return self._truncate(json.dumps(request.GET.dict(), ensure_ascii=True), max_chars)

        content_type = (request.content_type or "").split(";")[0].strip().lower()
        raw_body = self._safe_request_body(request)

        if content_type == "application/json":
            if raw_body is None:
                return "<unavailable: request stream already consumed>"
            if not raw_body:
                return "<empty>"
            try:
                parsed = json.loads(raw_body.decode("utf-8"))
                return self._truncate(json.dumps(parsed, ensure_ascii=True), max_chars)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._truncate(raw_body.decode("utf-8", errors="replace"), max_chars)

        if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
            payload = {
                "form": request.POST.dict(),
                "files": list(request.FILES.keys()),
            }
            return self._truncate(json.dumps(payload, ensure_ascii=True), max_chars)

        if raw_body is None:
            return "<unavailable: request stream already consumed>"
        if not raw_body:
            return "<empty>"

        return self._truncate(raw_body.decode("utf-8", errors="replace"), max_chars)

    def _response_payload(self, response, max_chars):
        if getattr(response, "streaming", False):
            return "<streaming-response>"

        try:
            content = getattr(response, "content", b"")
        except ContentNotRenderedError:
            return "<unavailable: template response not rendered yet>"
        if not content:
            return "<empty>"

        decoded = content.decode("utf-8", errors="replace")
        return self._truncate(decoded, max_chars)

    @staticmethod
    def _sanitize_headers(headers):
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def _truncate(text, max_chars):
        if text is None:
            return "<empty>"
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}...[truncated {len(text) - max_chars} chars]"

    @staticmethod
    def _safe_request_body(request):
        snapshot = getattr(request, "_api_debug_body_snapshot", None)
        if snapshot is not None:
            return snapshot
        # Prefer cached body when available; avoid forcing a second read from stream.
        if hasattr(request, "_body"):
            return request._body
        try:
            return request.body or b""
        except RawPostDataException:
            return None

    def _snapshot_request_body(self, request):
        request._api_debug_body_snapshot = self._safe_request_body(request)

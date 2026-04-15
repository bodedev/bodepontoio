import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from bodepontoio.middleware import APICallbackDebugMiddleware, install_debug_middleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_MW = "django.contrib.auth.middleware.AuthenticationMiddleware"
_DEBUG_MW = "bodepontoio.middleware.APICallbackDebugMiddleware"


def make_middleware(get_response=None):
    from django.http import HttpResponse
    if get_response is None:
        def get_response(req): return HttpResponse("ok", status=200)
    return APICallbackDebugMiddleware(get_response)


def enable_logger(settings_fixture, path_prefix="/api/", max_chars=6000):
    """Configure bodepontoio_settings for the debug logger and reload the cache."""
    from bodepontoio.conf import bodepontoio_settings
    settings_fixture.BODEPONTOIO = {
        "API_DEBUG_LOGGER_ENABLED": True,
        "API_DEBUG_LOGGER_PATH_PREFIX": path_prefix,
        "API_DEBUG_LOGGER_MAX_BODY_CHARS": max_chars,
    }
    bodepontoio_settings.reload()


def disable_logger(settings_fixture):
    from bodepontoio.conf import bodepontoio_settings
    settings_fixture.BODEPONTOIO = {"API_DEBUG_LOGGER_ENABLED": False}
    bodepontoio_settings.reload()


@pytest.fixture(autouse=True)
def reset_bodepontoio_settings():
    yield
    from bodepontoio.conf import bodepontoio_settings
    bodepontoio_settings.reload()


# ---------------------------------------------------------------------------
# install_debug_middleware
# ---------------------------------------------------------------------------

class TestInstallDebugMiddleware:
    def test_disabled_does_not_insert(self, settings):
        disable_logger(settings)
        result = install_debug_middleware([_AUTH_MW])
        assert _DEBUG_MW not in result

    def test_enabled_inserts_after_auth_middleware(self, settings):
        enable_logger(settings)
        mw = ["django.middleware.common.CommonMiddleware", _AUTH_MW, "django.middleware.csrf.CsrfViewMiddleware"]
        result = install_debug_middleware(mw)
        assert result.index(_DEBUG_MW) == result.index(_AUTH_MW) + 1

    def test_enabled_appends_when_no_auth_middleware(self, settings):
        enable_logger(settings)
        result = install_debug_middleware(["django.middleware.common.CommonMiddleware"])
        assert result[-1] == _DEBUG_MW

    def test_does_not_insert_duplicate(self, settings):
        enable_logger(settings)
        result = install_debug_middleware([_DEBUG_MW])
        assert result.count(_DEBUG_MW) == 1

    def test_does_not_mutate_original_list(self, settings):
        enable_logger(settings)
        original = [_AUTH_MW]
        install_debug_middleware(original)
        assert _DEBUG_MW not in original


# ---------------------------------------------------------------------------
# Passthrough when disabled / wrong path
# ---------------------------------------------------------------------------

class TestMiddlewarePassthrough:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_disabled_does_not_print(self, settings, capsys):
        disable_logger(settings)
        make_middleware()(self.factory.get("/api/test/"))
        assert capsys.readouterr().out == ""

    def test_non_matching_path_does_not_print(self, settings, capsys):
        enable_logger(settings)
        make_middleware()(self.factory.get("/admin/"))
        assert capsys.readouterr().out == ""

    def test_matching_path_prints_block(self, settings, capsys):
        enable_logger(settings)
        make_middleware()(self.factory.get("/api/test/"))
        output = capsys.readouterr().out
        assert "[API DEBUG] CALLBACK" in output
        assert "GET /api/test/" in output


# ---------------------------------------------------------------------------
# Output content
# ---------------------------------------------------------------------------

class TestMiddlewareOutput:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_response_status_in_output(self, settings, capsys):
        from django.http import HttpResponse
        enable_logger(settings)
        make_middleware(lambda req: HttpResponse("body", status=201))(self.factory.get("/api/x/"))
        assert "RESPONSE_STATUS: 201" in capsys.readouterr().out

    def test_duration_in_output(self, settings, capsys):
        enable_logger(settings)
        make_middleware()(self.factory.get("/api/x/"))
        assert "DURATION_MS:" in capsys.readouterr().out

    def test_sensitive_headers_are_redacted(self, settings, capsys):
        enable_logger(settings)
        request = self.factory.get("/api/x/", HTTP_AUTHORIZATION="Bearer secret-token")
        make_middleware()(request)
        output = capsys.readouterr().out
        assert "secret-token" not in output
        assert "<redacted>" in output

    def test_json_request_body_logged(self, settings, capsys):
        enable_logger(settings)
        payload = {"username": "alice", "value": 42}
        request = self.factory.post("/api/x/", data=json.dumps(payload), content_type="application/json")
        make_middleware()(request)
        assert "alice" in capsys.readouterr().out

    def test_get_query_params_logged(self, settings, capsys):
        enable_logger(settings)
        make_middleware()(self.factory.get("/api/x/", {"q": "hello"}))
        assert "hello" in capsys.readouterr().out

    def test_response_body_logged(self, settings, capsys):
        from django.http import HttpResponse
        enable_logger(settings)
        make_middleware(lambda req: HttpResponse('{"result": "ok"}', content_type="application/json"))(self.factory.get("/api/x/"))
        assert '"result"' in capsys.readouterr().out

    def test_anonymous_user_label(self, settings, capsys):
        enable_logger(settings)
        make_middleware()(self.factory.get("/api/x/"))
        assert "USER: anonymous" in capsys.readouterr().out

    def test_authenticated_user_label(self, settings, capsys):
        enable_logger(settings)
        request = self.factory.get("/api/x/")
        user = MagicMock()
        user.is_authenticated = True
        user.email = "alice@example.com"
        user.pk = 7
        request.user = user
        make_middleware()(request)
        output = capsys.readouterr().out
        assert "alice@example.com" in output
        assert "7" in output

    def test_form_post_logs_fields(self, settings, capsys):
        enable_logger(settings)
        request = self.factory.post("/api/x/", data={"field": "val"}, content_type="application/x-www-form-urlencoded")
        make_middleware()(request)
        assert "field" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

class TestMiddlewareTruncation:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_long_response_body_is_truncated(self, settings, capsys):
        from django.http import HttpResponse
        enable_logger(settings, max_chars=10)
        make_middleware(lambda req: HttpResponse("x" * 100))(self.factory.get("/api/x/"))
        assert "truncated" in capsys.readouterr().out

    def test_short_response_body_is_not_truncated(self, settings, capsys):
        from django.http import HttpResponse
        enable_logger(settings, max_chars=10)
        make_middleware(lambda req: HttpResponse("short"))(self.factory.get("/api/x/"))
        assert "truncated" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestMiddlewareEdgeCases:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_empty_response_body(self, settings, capsys):
        from django.http import HttpResponse
        enable_logger(settings)
        make_middleware(lambda req: HttpResponse("", status=204))(self.factory.get("/api/x/"))
        assert "<empty>" in capsys.readouterr().out

    def test_streaming_response(self, settings, capsys):
        from django.http import StreamingHttpResponse
        enable_logger(settings)
        make_middleware(lambda req: StreamingHttpResponse(iter([b"chunk"])))(self.factory.get("/api/x/"))
        assert "<streaming-response>" in capsys.readouterr().out

    def test_exception_in_print_does_not_break_response(self, settings):
        from django.http import HttpResponse
        enable_logger(settings)
        mw = make_middleware(lambda req: HttpResponse("ok"))
        with patch.object(APICallbackDebugMiddleware, "_print_debug_block", side_effect=RuntimeError("boom")):
            response = mw(self.factory.get("/api/x/"))
        assert response.status_code == 200

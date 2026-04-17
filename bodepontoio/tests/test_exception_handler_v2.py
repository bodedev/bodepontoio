import pytest
from rest_framework import exceptions, permissions
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from bodepontoio.exceptions import exception_handler_v2
from bodepontoio.mixins import BodepontoioMixin

factory = APIRequestFactory()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def call_handler(exc, view_instance=None):
    context = {"view": view_instance}
    return exception_handler_v2(exc, context)


class _PlainView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        raise exceptions.NotFound()


class _BodeView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        raise exceptions.NotFound()


class _BodeValidationView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        raise exceptions.ValidationError({"email": ["This field is required."]})


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestExceptionHandlerV2Unit:
    def test_opted_in_view_formats_not_found(self):
        exc = exceptions.NotFound()
        response = call_handler(exc, view_instance=_BodeView())
        assert response.data["success"] is False
        assert response.data["type"] == "not_found"
        assert "error" in response.data

    def test_opted_in_view_formats_validation_error(self):
        exc = exceptions.ValidationError({"email": ["Required."]})
        response = call_handler(exc, view_instance=_BodeView())
        assert response.data["success"] is False
        assert response.data["type"] == "validation_error"
        assert isinstance(response.data["errors"], list)

    def test_non_opted_in_view_returns_plain_drf_response(self):
        exc = exceptions.NotFound()
        response = call_handler(exc, view_instance=_PlainView())
        # Plain DRF formats as {"detail": "Not found."}
        assert "success" not in response.data
        assert "detail" in response.data

    def test_no_view_in_context_returns_plain_drf_response(self):
        exc = exceptions.NotFound()
        response = call_handler(exc, view_instance=None)
        assert "success" not in response.data
        assert "detail" in response.data

    def test_non_drf_exception_returns_none(self):
        response = call_handler(ValueError("boom"), view_instance=_BodeView())
        assert response is None

    def test_non_drf_exception_plain_view_returns_none(self):
        response = call_handler(ValueError("boom"), view_instance=_PlainView())
        assert response is None


# ---------------------------------------------------------------------------
# Integration tests — via test client with override_settings
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExceptionHandlerV2Integration:
    def test_bodepontoio_views_still_format_errors(self, api_client, settings):
        settings.REST_FRAMEWORK = {
            **settings.REST_FRAMEWORK,
            "EXCEPTION_HANDLER": "bodepontoio.exceptions.exception_handler_v2",
        }
        response = api_client.post("/auth/login/", {"email": "x@x.com", "password": "wrong"})
        body = response.json()
        assert body["success"] is False
        assert body["type"] == "validation_error"
        assert isinstance(body["errors"], list)

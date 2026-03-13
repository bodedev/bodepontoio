import pytest
from rest_framework import exceptions, status
from rest_framework.response import Response

from bodepontoio.exceptions import _flatten_errors, _get_error_type, exception_handler

CONTEXT = {}  # exception_handler only uses context for drf_exception_handler internals


# ---------------------------------------------------------------------------
# _get_error_type
# ---------------------------------------------------------------------------

class TestGetErrorType:
    def test_validation_error(self):
        assert _get_error_type(exceptions.ValidationError()) == "validation_error"

    def test_authentication_failed(self):
        assert _get_error_type(exceptions.AuthenticationFailed()) == "authentication_error"

    def test_not_authenticated(self):
        assert _get_error_type(exceptions.NotAuthenticated()) == "authentication_error"

    def test_permission_denied(self):
        assert _get_error_type(exceptions.PermissionDenied()) == "permission_error"

    def test_not_found(self):
        assert _get_error_type(exceptions.NotFound()) == "not_found"

    def test_parse_error(self):
        assert _get_error_type(exceptions.ParseError()) == "parse_error"

    def test_method_not_allowed(self):
        assert _get_error_type(exceptions.MethodNotAllowed("GET")) == "method_not_allowed"

    def test_throttled(self):
        assert _get_error_type(exceptions.Throttled()) == "throttled"

    def test_unknown_exception_falls_back_to_snake_case(self):
        class MyCustomError(exceptions.APIException):
            status_code = 400
        assert _get_error_type(MyCustomError()) == "my_custom_error"


# ---------------------------------------------------------------------------
# _flatten_errors
# ---------------------------------------------------------------------------

class TestFlattenErrors:
    def test_field_errors(self):
        data = {"email": ["This field is required."], "password": ["Too short."]}
        result = _flatten_errors(data)
        assert {"field": "email", "message": "This field is required."} in result
        assert {"field": "password", "message": "Too short."} in result

    def test_non_field_errors(self):
        data = {"non_field_errors": ["Invalid credentials."]}
        result = _flatten_errors(data)
        assert result == [{"field": "non_field_errors", "message": "Invalid credentials."}]

    def test_top_level_list(self):
        data = ["Some error."]
        result = _flatten_errors(data)
        assert result == [{"field": "non_field_errors", "message": "Some error."}]

    def test_nested_serializer_errors(self):
        data = {"address": {"city": ["This field is required."]}}
        result = _flatten_errors(data)
        assert result == [{"field": "address.city", "message": "This field is required."}]

    def test_multiple_messages_per_field(self):
        data = {"email": ["Not valid.", "Already taken."]}
        result = _flatten_errors(data)
        assert len(result) == 2
        assert all(e["field"] == "email" for e in result)


# ---------------------------------------------------------------------------
# exception_handler — validation errors
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExceptionHandlerValidation:
    def test_field_errors_shape(self, api_client, create_user):
        response = api_client.post("/auth/register/", {"email": "bad"})
        assert response.data["success"] is False
        assert response.data["type"] == "validation_error"
        assert isinstance(response.data["errors"], list)
        fields = [e["field"] for e in response.data["errors"]]
        assert "email" in fields or "password" in fields

    def test_non_field_error_shape(self, api_client):
        response = api_client.post(
            "/auth/login/", {"email": "x@x.com", "password": "wrongpass"}
        )
        assert response.data["success"] is False
        assert response.data["type"] == "validation_error"
        assert isinstance(response.data["errors"], list)


# ---------------------------------------------------------------------------
# exception_handler — other errors
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExceptionHandlerOther:
    def test_not_authenticated_shape(self, api_client):
        response = api_client.post("/auth/logout/", {"refresh": "token"})
        assert response.status_code == 401
        assert response.data["success"] is False
        assert response.data["type"] == "authentication_error"
        assert "error" in response.data

    def test_returns_none_for_unhandled_exceptions(self):
        result = exception_handler(ValueError("boom"), CONTEXT)
        assert result is None

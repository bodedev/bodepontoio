import json

import pytest
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from bodepontoio.renderers import SuccessJSONRenderer

factory = APIRequestFactory()


def render(data, status=200):
    """Helper: render data through SuccessJSONRenderer with a mock response."""
    response = Response(data, status=status)
    response.accepted_renderer = SuccessJSONRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {"response": response}
    rendered = SuccessJSONRenderer().render(
        data,
        accepted_media_type="application/json",
        renderer_context={"response": response},
    )
    return json.loads(rendered), response


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestSuccessJSONRenderer:
    def test_wraps_dict_in_data(self):
        result, _ = render({"access": "tok", "refresh": "tok"})
        assert result["success"] is True
        assert result["data"] == {"access": "tok", "refresh": "tok"}

    def test_wraps_list_in_data(self):
        result, _ = render([{"id": 1}, {"id": 2}])
        assert result["success"] is True
        assert result["data"] == [{"id": 1}, {"id": 2}]

    def test_empty_data_returns_success_true(self):
        result, response = render(None, status=204)
        assert result == {"success": True}
        assert response.status_code == 200

    def test_paginated_response(self):
        data = {
            "count": 42,
            "next": "http://example.com?page=2",
            "previous": None,
            "results": [{"id": 1}, {"id": 2}],
        }
        result, _ = render(data)
        assert result["success"] is True
        assert result["count"] == 42
        assert result["next"] == "http://example.com?page=2"
        assert result["previous"] is None
        assert result["data"] == [{"id": 1}, {"id": 2}]
        assert "results" not in result

    def test_error_responses_pass_through(self):
        error_data = {"success": False, "type": "not_found", "error": "Not found."}
        result, _ = render(error_data, status=404)
        assert result == error_data


# ---------------------------------------------------------------------------
# Integration tests — check wire format via response.json()
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRendererIntegration:
    def test_login_wire_format(self, api_client, create_user):
        create_user(email="render@example.com", password="testpassword123", is_email_verified=True)
        response = api_client.post(
            "/auth/login/",
            {"email": "render@example.com", "password": "testpassword123"},
        )
        body = response.json()
        assert body["success"] is True
        assert "access" in body["data"]
        assert "refresh" in body["data"]

    def test_register_wire_format(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {
                "email": "renderreg@example.com",
                "password": "securepassword123",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], str)

    def test_logout_wire_format(self, auth_client):
        client, user = auth_client
        refresh = RefreshToken.for_user(user)
        response = client.post("/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == 200
        body = response.json()
        assert body == {"success": True}

    def test_error_wire_format_not_wrapped(self, api_client):
        response = api_client.post(
            "/auth/login/", {"email": "x@x.com", "password": "wrong"}
        )
        body = response.json()
        assert body["success"] is False
        assert "data" not in body

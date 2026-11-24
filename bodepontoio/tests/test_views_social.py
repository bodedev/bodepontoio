from unittest.mock import patch

from django.test import override_settings
from google.auth import exceptions as google_exceptions

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

GOOGLE_URL = reverse("bodepontoio:social-google")
MOCK_TARGET = "bodepontoio.serializers.google_id_token.verify_oauth2_token"


def make_id_info(email="user@example.com", given_name="John", family_name="Doe", **overrides):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "test-client-id.apps.googleusercontent.com",
        "email": email,
        "email_verified": True,
        "given_name": given_name,
        "family_name": family_name,
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestGoogleLoginView:
    def test_new_user_gets_tokens(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info()):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" in data
        assert "refresh" in data

    def test_new_user_has_unusable_password(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info(email="new@example.com")):
            client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        user = User.objects.get(email="new@example.com")
        assert not user.has_usable_password()

    def test_new_user_gets_name_from_google(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info(email="named@example.com", given_name="Jane", family_name="Smith")):
            client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        user = User.objects.get(email="named@example.com")
        assert user.first_name == "Jane"
        assert user.last_name == "Smith"

    def test_existing_user_returns_tokens(self, client):
        User.objects.create_user(username="existing", email="existing@example.com", password="pass")
        with patch(MOCK_TARGET, return_value=make_id_info(email="existing@example.com")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 200
        assert User.objects.filter(email="existing@example.com").count() == 1

    def test_invalid_token_returns_401(self, client):
        with patch(MOCK_TARGET, side_effect=ValueError("bad token")):
            response = client.post(GOOGLE_URL, {"id_token": "bad-token"}, format="json")
        assert response.status_code == 401
        assert response.json()["type"] == "authentication_error"

    def test_missing_id_token_returns_400(self, client):
        response = client.post(GOOGLE_URL, {}, format="json")
        assert response.status_code == 400
        assert response.json()["type"] == "validation_error"

    def test_inactive_user_returns_401(self, client):
        User.objects.create_user(username="inactive@example.com", email="inactive@example.com", password="pass", is_active=False)
        with patch(MOCK_TARGET, return_value=make_id_info(email="inactive@example.com")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401
        assert response.json()["type"] == "authentication_error"

    def test_unverified_email_returns_401_and_does_not_touch_the_account(self, client):
        user = User.objects.create_user(username="victim@example.com", email="victim@example.com", password="pass")
        with patch(MOCK_TARGET, return_value=make_id_info(email="victim@example.com", email_verified=False)):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401
        user.auth.refresh_from_db()
        assert not user.auth.is_email_verified

    def test_missing_email_verified_claim_returns_401(self, client):
        info = make_id_info(email="nobody@example.com")
        del info["email_verified"]
        with patch(MOCK_TARGET, return_value=info):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401
        assert not User.objects.filter(email="nobody@example.com").exists()

    def test_email_verified_as_string_returns_401(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info(email_verified="true")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401

    def test_unknown_audience_returns_401(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info(aud="someone-else.apps.googleusercontent.com")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401

    def test_wrong_issuer_returns_401(self, client):
        with patch(MOCK_TARGET, side_effect=google_exceptions.GoogleAuthError("Wrong issuer")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 401

    def test_extra_client_ids_are_accepted(self, client):
        settings_override = {
            "GOOGLE_CLIENT_ID": "web.apps.googleusercontent.com",
            "GOOGLE_CLIENT_IDS": ["ios.apps.googleusercontent.com"],
        }
        with override_settings(BODEPONTOIO=settings_override):
            with patch(MOCK_TARGET, return_value=make_id_info(aud="ios.apps.googleusercontent.com")):
                response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 200

    def test_audience_check_is_not_left_to_google_auth(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info()) as verify:
            client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert verify.call_args.args[2] is None

    def test_inactive_user_email_is_not_marked_verified(self, client):
        user = User.objects.create_user(
            username="off@example.com", email="off@example.com", password="pass", is_active=False
        )
        with patch(MOCK_TARGET, return_value=make_id_info(email="off@example.com")):
            client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        user.auth.refresh_from_db()
        assert not user.auth.is_email_verified

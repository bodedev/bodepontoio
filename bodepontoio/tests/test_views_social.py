from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

GOOGLE_URL = reverse("bodepontoio:social-google")
MOCK_TARGET = "bodepontoio.serializers.google_id_token.verify_oauth2_token"


def make_id_info(email="user@example.com", given_name="John", family_name="Doe"):
    return {"email": email, "given_name": given_name, "family_name": family_name}


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
        user = User.objects.get(username="new@example.com")
        assert not user.has_usable_password()

    def test_new_user_gets_name_from_google(self, client):
        with patch(MOCK_TARGET, return_value=make_id_info(email="named@example.com", given_name="Jane", family_name="Smith")):
            client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        user = User.objects.get(username="named@example.com")
        assert user.first_name == "Jane"
        assert user.last_name == "Smith"

    def test_existing_user_returns_tokens(self, client):
        User.objects.create_user(username="existing@example.com", email="existing@example.com", password="pass")
        with patch(MOCK_TARGET, return_value=make_id_info(email="existing@example.com")):
            response = client.post(GOOGLE_URL, {"id_token": "valid-token"}, format="json")
        assert response.status_code == 200
        assert User.objects.filter(username="existing@example.com").count() == 1

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

import pytest
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestLoginView:
    def test_login_success(self, api_client, create_user):
        create_user(email="login@example.com", password="testpassword123")
        response = api_client.post(
            "/auth/login/",
            {"email": "login@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_invalid_credentials(self, api_client):
        response = api_client.post(
            "/auth/login/",
            {"email": "wrong@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 400

    def test_login_missing_password(self, api_client):
        response = api_client.post("/auth/login/", {"email": "test@example.com"})
        assert response.status_code == 400

    def test_login_missing_email(self, api_client):
        response = api_client.post("/auth/login/", {"password": "somepassword"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_success(self, auth_client):
        client, user = auth_client
        refresh = RefreshToken.for_user(user)
        response = client.post("/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == 200

    def test_logout_unauthenticated(self, api_client):
        response = api_client.post("/auth/logout/", {"refresh": "sometoken"})
        assert response.status_code == 401

    def test_logout_invalid_token(self, auth_client):
        client, _ = auth_client
        response = client.post("/auth/logout/", {"refresh": "invalidtoken"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestRegisterView:
    def test_register_success(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {
                "email": "newuser@example.com",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 201
        assert isinstance(response.data, str)

    def test_register_duplicate_email(self, api_client, create_user):
        create_user(email="existing@example.com")
        response = api_client.post(
            "/auth/register/",
            {
                "email": "existing@example.com",
                "password": "securepassword123",
                "first_name": "Another",
                "last_name": "User",
            },
        )
        assert response.status_code == 400

    def test_register_weak_password(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {
                "email": "weak@example.com",
                "password": "short",
                "first_name": "Weak",
                "last_name": "User",
            },
        )
        assert response.status_code == 400

    def test_register_missing_email(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {"password": "securepassword123", "first_name": "No", "last_name": "Email"},
        )
        assert response.status_code == 400

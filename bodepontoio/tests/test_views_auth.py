import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestLoginView:
    def test_login_with_email(self, api_client, create_user):
        create_user(email="login@example.com", password="testpassword123", is_email_verified=True)
        response = api_client.post(
            "/auth/login/",
            {"login": "login@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_with_username(self, api_client, create_user):
        create_user(email="login2@example.com", password="testpassword123", is_email_verified=True, username="myusername")
        response = api_client.post(
            "/auth/login/",
            {"login": "myusername", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_invalid_credentials(self, api_client):
        response = api_client.post(
            "/auth/login/",
            {"login": "wrong@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 400

    def test_login_missing_password(self, api_client):
        response = api_client.post("/auth/login/", {"login": "test@example.com"})
        assert response.status_code == 400

    def test_login_missing_login(self, api_client):
        response = api_client.post("/auth/login/", {"password": "somepassword"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestTokenRefreshView:
    def test_refresh_success(self, api_client, create_user):
        user = create_user()
        refresh = RefreshToken.for_user(user)
        response = api_client.post("/auth/token/refresh/", {"refresh": str(refresh)})
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_refresh_invalid_token(self, api_client):
        response = api_client.post("/auth/token/refresh/", {"refresh": "invalidtoken"})
        assert response.status_code == 400

    def test_refresh_missing_token(self, api_client):
        response = api_client.post("/auth/token/refresh/", {})
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
                "username": "newuser",
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
                "username": "anotheruser",
                "email": "existing@example.com",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 400

    def test_register_duplicate_username(self, api_client, create_user):
        create_user(email="first@example.com", username="takenuser")
        response = api_client.post(
            "/auth/register/",
            {
                "username": "takenuser",
                "email": "second@example.com",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 400

    def test_register_weak_password(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 400

    def test_register_missing_email(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {"username": "nomail", "password": "securepassword123"},
        )
        assert response.status_code == 400

    def test_register_without_username_auto_generates_one(self, api_client):
        response = api_client.post(
            "/auth/register/",
            {"email": "nouser@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 201


import pytest


@pytest.mark.django_db
class TestDefaultUserSerializer:
    def test_returns_expected_fields(self, create_user):
        user = create_user(
            email="serial@example.com",
            first_name="Ada",
            last_name="Lovelace",
        )
        from bodepontoio.serializers import DefaultUserSerializer
        data = DefaultUserSerializer(user).data
        assert data["id"] == user.pk
        assert data["email"] == "serial@example.com"
        assert data["first_name"] == "Ada"
        assert data["last_name"] == "Lovelace"
        assert set(data.keys()) == {"id", "email", "first_name", "last_name"}


class TestGetUserSerializerClass:
    def test_default_resolves_to_default_serializer(self):
        from bodepontoio.serializers import DefaultUserSerializer, get_user_serializer_class
        assert get_user_serializer_class() is DefaultUserSerializer

    @override_settings(BODEPONTOIO={"USER_SERIALIZER": None})
    def test_none_returns_none(self):
        from bodepontoio.serializers import get_user_serializer_class
        assert get_user_serializer_class() is None

    @override_settings(BODEPONTOIO={"USER_SERIALIZER": "does.not.exist.Serializer"})
    def test_bad_path_raises_improperly_configured(self):
        from bodepontoio.serializers import get_user_serializer_class
        with pytest.raises(ImproperlyConfigured):
            get_user_serializer_class()

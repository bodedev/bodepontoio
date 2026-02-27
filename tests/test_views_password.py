import pytest
from django.core import mail

from bodepontoio.tokens import make_reset_token, make_uid


@pytest.mark.django_db
class TestPasswordChangeView:
    def test_change_password_success(self, auth_client):
        client, user = auth_client
        response = client.post(
            "/auth/password/change/",
            {"old_password": "testpassword123", "new_password": "newpassword456"},
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("newpassword456")

    def test_change_password_wrong_old(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/auth/password/change/",
            {"old_password": "wrongpassword", "new_password": "newpassword456"},
        )
        assert response.status_code == 400

    def test_change_password_unauthenticated(self, api_client):
        response = api_client.post(
            "/auth/password/change/",
            {"old_password": "testpassword123", "new_password": "newpassword456"},
        )
        assert response.status_code == 401

    def test_change_password_too_short(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/auth/password/change/",
            {"old_password": "testpassword123", "new_password": "short"},
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestPasswordResetRequestView:
    def test_reset_request_existing_user(self, api_client, create_user):
        create_user(email="resetme@example.com")
        response = api_client.post(
            "/auth/password/reset/", {"email": "resetme@example.com"}
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "resetme@example.com" in mail.outbox[0].to

    def test_reset_request_unknown_email(self, api_client):
        response = api_client.post(
            "/auth/password/reset/", {"email": "nobody@example.com"}
        )
        assert response.status_code == 200  # Anti-enumeration: always 200
        assert len(mail.outbox) == 0

    def test_reset_request_invalid_email(self, api_client):
        response = api_client.post("/auth/password/reset/", {"email": "not-an-email"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestPasswordResetConfirmView:
    def test_reset_confirm_success(self, api_client, create_user):
        user = create_user(email="confirm@example.com")
        uid = make_uid(user)
        token = make_reset_token(user)
        response = api_client.post(
            "/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("brandnewpassword")

    def test_reset_confirm_invalid_token(self, api_client, create_user):
        user = create_user(email="badtoken@example.com")
        uid = make_uid(user)
        response = api_client.post(
            "/auth/password/reset/confirm/",
            {"uid": uid, "token": "invalidtoken", "new_password": "brandnewpassword"},
        )
        assert response.status_code == 400

    def test_reset_confirm_invalid_uid(self, api_client):
        response = api_client.post(
            "/auth/password/reset/confirm/",
            {
                "uid": "!!!invalid!!!",
                "token": "sometoken",
                "new_password": "brandnewpassword",
            },
        )
        assert response.status_code == 400

    def test_reset_confirm_weak_password(self, api_client, create_user):
        user = create_user(email="weakreset@example.com")
        uid = make_uid(user)
        token = make_reset_token(user)
        response = api_client.post(
            "/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "short"},
        )
        assert response.status_code == 400

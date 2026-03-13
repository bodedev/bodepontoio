import pytest
from django.core import mail

from bodepontoio.tokens import make_confirmation_token, make_uid


@pytest.mark.django_db
class TestEmailConfirmation:
    def test_register_sends_confirmation_email(self, api_client):
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
        assert len(mail.outbox) == 1
        assert "newuser@example.com" in mail.outbox[0].to

    def test_unconfirmed_user_cannot_login(self, api_client, create_user):
        create_user(email="unconfirmed@example.com", password="testpassword123")
        response = api_client.post(
            "/auth/login/",
            {"email": "unconfirmed@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 400

    def test_confirmed_user_can_login(self, api_client, create_user):
        create_user(
            email="confirmed@example.com",
            password="testpassword123",
            is_email_verified=True,
        )
        response = api_client.post(
            "/auth/login/",
            {"email": "confirmed@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data

    def test_confirm_email_success(self, api_client, create_user):
        user = create_user(email="toconfirm@example.com")
        uid = make_uid(user)
        token = make_confirmation_token(user)
        response = api_client.get(f"/auth/email/confirm/{uid}/{token}/")
        assert response.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.is_email_verified is True

    def test_confirm_email_invalid_token(self, api_client, create_user):
        user = create_user(email="badtoken@example.com")
        uid = make_uid(user)
        response = api_client.get(f"/auth/email/confirm/{uid}/invalidtoken/")
        assert response.status_code == 400

    def test_confirm_email_invalid_uid(self, api_client):
        response = api_client.get("/auth/email/confirm/notavaliduid/sometoken/")
        assert response.status_code == 400

    def test_confirm_email_idempotent(self, api_client, create_user):
        user = create_user(email="idempotent@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_confirmation_token(user)
        response = api_client.get(f"/auth/email/confirm/{uid}/{token}/")
        assert response.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.is_email_verified is True

    def test_resend_sends_email_to_unverified_user(self, api_client, create_user):
        create_user(email="resend@example.com")
        response = api_client.post(
            "/auth/email/confirm/resend/",
            {"email": "resend@example.com"},
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "resend@example.com" in mail.outbox[0].to

    def test_resend_silent_for_unknown_email(self, api_client):
        response = api_client.post(
            "/auth/email/confirm/resend/",
            {"email": "nobody@example.com"},
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    def test_resend_silent_for_already_verified(self, api_client, create_user):
        create_user(email="verified@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/email/confirm/resend/",
            {"email": "verified@example.com"},
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 0

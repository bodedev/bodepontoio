import pytest
from datetime import timedelta
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from bodepontoio.models import OTPCode
from bodepontoio.otp import generate_otp


OTP_STRATEGY = {
    "LOGIN_STRATEGY": "otp",
    "OTP_LENGTH": 6,
    "OTP_EXPIRY_SECONDS": 900,
    "OTP_MAX_ATTEMPTS": 5,
}


@pytest.mark.django_db
class TestLoginOTPRequest:
    """POST login/ when LOGIN_STRATEGY = "otp" sends a code instead of checking a password."""

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_sends_otp_email(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "user@example.com" in mail.outbox[0].to

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_email_body_contains_code(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        otp = OTPCode.objects.get(purpose=OTPCode.Purpose.LOGIN)
        assert otp.code in mail.outbox[0].body

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_anti_enumeration_unknown_email(self, api_client):
        response = api_client.post("/auth/login/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_anti_enumeration_inactive_user(self, api_client, create_user):
        user = create_user(email="inactive@example.com")
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post("/auth/login/", {"email": "inactive@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestLoginOTPConfirm:
    """POST login/otp/confirm/ exchanges a valid code for JWT tokens."""

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_success_returns_tokens(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_auto_verifies_email(self, api_client, create_user):
        user = create_user(email="unverified@example.com", is_email_verified=False)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        api_client.post("/auth/login/otp/confirm/", {"email": user.email, "code": otp.code})
        user.auth.refresh_from_db()
        assert user.auth.is_email_verified is True

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_wrong_code(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        generate_otp(user, OTPCode.Purpose.LOGIN)
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": "000000"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_expired_code(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_inactive_user(self, api_client, create_user):
        user = create_user(email="inactive@example.com", is_email_verified=True)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_unknown_email(self, api_client):
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": "nobody@example.com", "code": "123456"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_max_attempts_burns_code(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        for _ in range(5):
            api_client.post(
                "/auth/login/otp/confirm/",
                {"email": user.email, "code": "000000"},
            )
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 400

    def test_returns_404_when_strategy_is_password(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        response = api_client.post(
            "/auth/login/otp/confirm/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestLoginStrategyBehavior:
    """login/ behaves differently depending on LOGIN_STRATEGY."""

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_otp_strategy_login_accepts_email_field(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_otp_strategy_login_does_not_return_tokens_directly(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert "access" not in response.data
        assert "refresh" not in response.data

    def test_password_strategy_login_accepts_credentials(self, api_client, create_user):
        create_user(email="user@example.com", password="testpassword123", is_email_verified=True)
        response = api_client.post(
            "/auth/login/",
            {"login": "user@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_password_strategy_credentials_rejected_when_otp(self, api_client, create_user):
        create_user(email="user@example.com", password="testpassword123", is_email_verified=True)
        response = api_client.post(
            "/auth/login/",
            {"login": "user@example.com", "password": "testpassword123"},
        )
        # login/password fields are not valid for the OTP serializer
        assert response.status_code == 400

from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from bodepontoio.models import OTPCode
from bodepontoio.otp import generate_otp
from bodepontoio.tokens import make_confirmation_token, make_uid

OTP_STRATEGY = {"EMAIL_CONFIRM_STRATEGY": "otp", "OTP_LENGTH": 6, "OTP_EXPIRY_SECONDS": 900, "OTP_MAX_ATTEMPTS": 5}


@pytest.mark.django_db
class TestOTPEmailConfirmation:
    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_register_sends_otp_email(self, api_client):
        api_client.post(
            "/auth/register/",
            {"email": "newuser@example.com", "password": "securepassword123"},
        )
        assert len(mail.outbox) == 1
        assert "newuser@example.com" in mail.outbox[0].to
        assert OTPCode.objects.filter(purpose=OTPCode.Purpose.EMAIL_CONFIRM).exists()

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_register_email_body_contains_code(self, api_client):
        api_client.post(
            "/auth/register/",
            {"email": "codecheck@example.com", "password": "securepassword123"},
        )
        otp = OTPCode.objects.get(purpose=OTPCode.Purpose.EMAIL_CONFIRM)
        assert otp.code in mail.outbox[0].body

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_otp_success(self, api_client, create_user):
        user = create_user(email="confirmme@example.com")
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 200
        user.auth.refresh_from_db()
        assert user.auth.is_email_verified is True

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_otp_wrong_code(self, api_client, create_user):
        user = create_user(email="wrongcode@example.com")
        generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": user.email, "code": "000000"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_otp_expired(self, api_client, create_user):
        user = create_user(email="expired@example.com")
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_otp_unknown_email(self, api_client):
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": "nobody@example.com", "code": "123456"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_otp_max_attempts_burns_code(self, api_client, create_user):
        user = create_user(email="maxattempts@example.com")
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        for _ in range(5):
            api_client.post(
                "/auth/email/confirm/otp/",
                {"email": user.email, "code": "000000"},
            )
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 400
        user.auth.refresh_from_db()
        assert user.auth.is_email_verified is False

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_resend_sends_new_otp(self, api_client, create_user):
        user = create_user(email="resend@example.com")
        first_otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        api_client.post("/auth/email/confirm/resend/", {"email": user.email})
        first_otp.refresh_from_db()
        assert first_otp.is_used is True
        assert len(mail.outbox) == 1
        new_otp = OTPCode.objects.filter(
            user=user, purpose=OTPCode.Purpose.EMAIL_CONFIRM, is_used=False
        ).first()
        assert new_otp is not None
        assert new_otp.pk != first_otp.pk

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_resend_response_mentions_codigo(self, api_client, create_user):
        create_user(email="resend2@example.com")
        response = api_client.post("/auth/email/confirm/resend/", {"email": "resend2@example.com"})
        assert response.status_code == 200
        assert "código" in response.data.lower()

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_magic_link_endpoint_still_works_when_strategy_is_otp(self, api_client, create_user):
        user = create_user(email="magicotp@example.com")
        uid = make_uid(user)
        token = make_confirmation_token(user)
        response = api_client.get(f"/auth/email/confirm/{uid}/{token}/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestOTPEmailConfirmEndpointWhenStrategyIsMagicLink:
    """Verify OTP endpoint returns 404 when strategy is the default magic_link."""

    def test_otp_endpoint_returns_404(self, api_client, create_user):
        user = create_user(email="magiconly@example.com")
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        response = api_client.post(
            "/auth/email/confirm/otp/",
            {"email": user.email, "code": otp.code},
        )
        assert response.status_code == 404

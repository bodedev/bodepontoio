import pytest
from datetime import timedelta
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from bodepontoio.models import OTPCode
from bodepontoio.otp import generate_otp
from bodepontoio.tokens import make_reset_token, make_uid


OTP_STRATEGY = {"PASSWORD_RESET_STRATEGY": "otp", "OTP_LENGTH": 6, "OTP_EXPIRY_SECONDS": 900, "OTP_MAX_ATTEMPTS": 5}


@pytest.mark.django_db
class TestOTPPasswordReset:
    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_request_sends_otp_email(self, api_client, create_user):
        create_user(email="resetme@example.com")
        response = api_client.post("/auth/password/reset/", {"email": "resetme@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "resetme@example.com" in mail.outbox[0].to

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_request_email_body_contains_code(self, api_client, create_user):
        create_user(email="codecheck@example.com")
        api_client.post("/auth/password/reset/", {"email": "codecheck@example.com"})
        otp = OTPCode.objects.get(purpose=OTPCode.Purpose.PASSWORD_RESET)
        assert otp.code in mail.outbox[0].body

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_request_response_mentions_codigo(self, api_client, create_user):
        create_user(email="msgcheck@example.com")
        response = api_client.post("/auth/password/reset/", {"email": "msgcheck@example.com"})
        assert "código" in response.data.lower()

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_request_anti_enumeration(self, api_client):
        response = api_client.post("/auth/password/reset/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_success(self, api_client, create_user):
        user = create_user(email="confirm@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("brandnewpassword")

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_marks_otp_as_used(self, api_client, create_user):
        user = create_user(email="used@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "brandnewpassword"},
        )
        otp.refresh_from_db()
        assert otp.is_used is True

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_wrong_code(self, api_client, create_user):
        user = create_user(email="wrongcode@example.com")
        generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": "000000", "new_password": "brandnewpassword"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_expired_code(self, api_client, create_user):
        user = create_user(email="expired@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_unknown_email(self, api_client):
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": "nobody@example.com", "code": "123456", "new_password": "brandnewpassword"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_weak_password(self, api_client, create_user):
        user = create_user(email="weakpass@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "short"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_reset_confirm_max_attempts_burns_code(self, api_client, create_user):
        user = create_user(email="maxattempts@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        for _ in range(5):
            api_client.post(
                "/auth/password/reset/confirm/otp/",
                {"email": user.email, "code": "000000", "new_password": "brandnewpassword"},
            )
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password("testpassword123")

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_magic_link_confirm_still_works_when_strategy_is_otp(self, api_client, create_user):
        user = create_user(email="magicstillworks@example.com")
        uid = make_uid(user)
        token = make_reset_token(user)
        response = api_client.post(
            "/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestOTPPasswordResetEndpointWhenStrategyIsMagicLink:
    """Verify OTP endpoint returns 404 when strategy is the default magic_link."""

    def test_otp_endpoint_returns_404(self, api_client, create_user):
        user = create_user(email="magiconly@example.com")
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        response = api_client.post(
            "/auth/password/reset/confirm/otp/",
            {"email": user.email, "code": otp.code, "new_password": "brandnewpassword"},
        )
        assert response.status_code == 404

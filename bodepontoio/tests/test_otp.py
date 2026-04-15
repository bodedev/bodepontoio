import pytest
from datetime import timedelta
from django.test import override_settings
from django.utils import timezone

from bodepontoio.models import OTPCode
from bodepontoio.otp import generate_otp, verify_otp


OTP_SETTINGS = {
    "OTP_LENGTH": 6,
    "OTP_EXPIRY_SECONDS": 900,
    "OTP_MAX_ATTEMPTS": 5,
}


@pytest.mark.django_db
class TestGenerateOTP:
    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_creates_code_with_correct_length(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        assert len(otp.code) == 6

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_code_contains_only_digits(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        assert otp.code.isdigit()

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_sets_correct_purpose(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        assert otp.purpose == OTPCode.Purpose.PASSWORD_RESET

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_sets_expiry_from_settings(self, create_user):
        user = create_user()
        before = timezone.now()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        after = timezone.now()
        assert before + timedelta(seconds=900) <= otp.expires_at <= after + timedelta(seconds=900)

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_invalidates_previous_unused_codes(self, create_user):
        user = create_user()
        first = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        second = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        first.refresh_from_db()
        assert first.is_used is True
        assert second.is_used is False

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_does_not_invalidate_other_purpose(self, create_user):
        user = create_user()
        email_otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        generate_otp(user, OTPCode.Purpose.PASSWORD_RESET)
        email_otp.refresh_from_db()
        assert email_otp.is_used is False

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_does_not_invalidate_other_users_codes(self, create_user):
        user_a = create_user(email="a@example.com")
        user_b = create_user(email="b@example.com")
        otp_a = generate_otp(user_a, OTPCode.Purpose.EMAIL_CONFIRM)
        generate_otp(user_b, OTPCode.Purpose.EMAIL_CONFIRM)
        otp_a.refresh_from_db()
        assert otp_a.is_used is False


@pytest.mark.django_db
class TestVerifyOTP:
    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_success(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        success, error = verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is True
        assert error == ""

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_marks_as_used_on_success(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        otp.refresh_from_db()
        assert otp.is_used is True

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_wrong_code_returns_error(self, create_user):
        user = create_user()
        generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        success, error = verify_otp(user, "000000", OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is False
        assert error != ""

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_wrong_code_increments_attempts(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        verify_otp(user, "000000", OTPCode.Purpose.EMAIL_CONFIRM)
        otp.refresh_from_db()
        assert otp.attempts == 1

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_expired_code_returns_error(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])
        success, error = verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is False
        assert "expirado" in error.lower()

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_expired_code_is_marked_as_used(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])
        verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        otp.refresh_from_db()
        assert otp.is_used is True

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_already_used_code_fails(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        success, _ = verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is False

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_no_codes_exist_returns_error(self, create_user):
        user = create_user()
        success, _ = verify_otp(user, "123456", OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is False

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_max_attempts_burns_code(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        for _ in range(5):
            verify_otp(user, "000000", OTPCode.Purpose.EMAIL_CONFIRM)
        otp.refresh_from_db()
        assert otp.is_used is True

    @override_settings(BODEPONTOIO=OTP_SETTINGS)
    def test_correct_code_after_max_attempts_fails(self, create_user):
        user = create_user()
        otp = generate_otp(user, OTPCode.Purpose.EMAIL_CONFIRM)
        for _ in range(5):
            verify_otp(user, "000000", OTPCode.Purpose.EMAIL_CONFIRM)
        success, _ = verify_otp(user, otp.code, OTPCode.Purpose.EMAIL_CONFIRM)
        assert success is False

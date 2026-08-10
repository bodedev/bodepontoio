"""Every email that mentions a deadline must state the real one.

The reset and confirmation templates used to hardcode "expira em 24 horas" while
both tokens actually live for PASSWORD_RESET_TIMEOUT -- three days by default, so
users were sent back for a new link two days early. Worse, a project that lowers
PASSWORD_RESET_TIMEOUT got the error the other way round: the email promised 24
hours for a link that was already dead.

Django templates swallow unknown variables, so a typo in the expiry context ships
"expira em ." with nothing failing. These assertions are the only guard.
"""

import pytest
from django.core import mail
from django.test import override_settings

from bodepontoio.emails import _expiry, send_email_confirmation_email, send_password_reset_email


def _html(message):
    return message.alternatives[0][0]


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "1 minuto"),  # never "0 minutos"
        (30, "1 minuto"),
        (60, "1 minuto"),
        (90, "2 minutos"),  # rounds up: never promise less than there is
        (900, "15 minutos"),
        (3600, "60 minutos"),  # under two hours still reads in minutes
        (5400, "90 minutos"),
        (7200, "2 horas"),
        (9000, "3 horas"),  # 2.5h rounds up
        (259200, "72 horas"),  # Django's three-day default
    ],
)
def test_expiry_phrase(seconds, expected):
    assert _expiry(seconds)["expiry_phrase"] == expected


@pytest.mark.django_db
class TestLinkEmailsStateTheRealDeadline:
    def test_password_reset_link_uses_password_reset_timeout(self, create_user):
        user = create_user(email="user@example.com")
        send_password_reset_email(user)
        assert "expira em 72 horas" in _html(mail.outbox[0])

    @override_settings(PASSWORD_RESET_TIMEOUT=3600)
    def test_password_reset_link_follows_a_lowered_timeout(self, create_user):
        user = create_user(email="user@example.com")
        send_password_reset_email(user)
        assert "expira em 60 minutos" in _html(mail.outbox[0])

    def test_email_confirmation_link_uses_password_reset_timeout(self, create_user):
        user = create_user(email="user@example.com")
        send_email_confirmation_email(user, request=None)
        assert "expira em 72 horas" in _html(mail.outbox[0])


@pytest.mark.django_db
class TestOTPEmailsPluralize:
    """OTP_EXPIRY_SECONDS // 60 used to print "1 minutos" for a 90-second code,
    and "0 minutos" for anything under a minute."""

    @override_settings(
        BODEPONTOIO={"PASSWORD_RESET_STRATEGY": "otp", "OTP_EXPIRY_SECONDS": 60}
    )
    def test_single_minute_is_not_pluralized(self, create_user):
        user = create_user(email="user@example.com")
        send_password_reset_email(user)
        assert "expira em 1 minuto." in _html(mail.outbox[0])
        assert "expira em 1 minuto." in mail.outbox[0].body

    @override_settings(
        BODEPONTOIO={"PASSWORD_RESET_STRATEGY": "otp", "OTP_EXPIRY_SECONDS": 90}
    )
    def test_partial_minutes_round_up(self, create_user):
        user = create_user(email="user@example.com")
        send_password_reset_email(user)
        assert "expira em 2 minutos." in _html(mail.outbox[0])

    @override_settings(
        BODEPONTOIO={"PASSWORD_RESET_STRATEGY": "otp", "OTP_EXPIRY_SECONDS": 900}
    )
    def test_many_minutes_are_pluralized(self, create_user):
        user = create_user(email="user@example.com")
        send_password_reset_email(user)
        assert "expira em 15 minutos." in _html(mail.outbox[0])
        assert "expira em 15 minutos." in mail.outbox[0].body

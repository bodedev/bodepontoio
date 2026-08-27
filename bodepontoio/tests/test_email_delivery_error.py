from smtplib import SMTPServerDisconnected

import pytest
from django.test import override_settings

from bodepontoio.emails import send_mail
from bodepontoio.exceptions import EmailDeliveryError

MAGIC_LINK_STRATEGY = {"LOGIN_STRATEGY": "magic_link"}


class TestSendMailWrapper:
    """An unreachable/misbehaving SMTP relay should surface as EmailDeliveryError,
    not as whatever smtplib/socket exception the relay happened to raise."""

    def test_smtp_exception_becomes_email_delivery_error(self, monkeypatch):
        def boom(**kwargs):
            raise SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)
        with pytest.raises(EmailDeliveryError):
            send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])

    def test_socket_timeout_becomes_email_delivery_error(self, monkeypatch):
        def boom(**kwargs):
            raise TimeoutError("timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)
        with pytest.raises(EmailDeliveryError):
            send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])

    def test_other_exceptions_are_not_swallowed(self, monkeypatch):
        def boom(**kwargs):
            raise ValueError("template blew up")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)
        with pytest.raises(ValueError):
            send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])


class TestSendMailRetries:
    """EMAIL_SEND_RETRIES controls how many extra attempts follow the first failure."""

    def test_succeeds_on_a_later_attempt_within_the_retry_budget(self, monkeypatch):
        calls = []

        def flaky(**kwargs):
            calls.append(1)
            if len(calls) < 2:
                raise SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", flaky)
        send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])
        assert len(calls) == 2

    def test_gives_up_after_configured_retries(self, monkeypatch):
        calls = []

        def boom(**kwargs):
            calls.append(1)
            raise SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)
        with override_settings(BODEPONTOIO={"EMAIL_SEND_RETRIES": 2}), pytest.raises(EmailDeliveryError):
            send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])
        assert len(calls) == 3

    def test_zero_retries_fails_after_a_single_attempt(self, monkeypatch):
        calls = []

        def boom(**kwargs):
            calls.append(1)
            raise SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)
        with override_settings(BODEPONTOIO={"EMAIL_SEND_RETRIES": 0}), pytest.raises(EmailDeliveryError):
            send_mail(subject="s", message="m", from_email="a@example.com", recipient_list=["b@example.com"])
        assert len(calls) == 1


@pytest.mark.django_db
class TestLoginViewSmtpFailure:
    """The login endpoint should return a handled 503 envelope, not an unhandled 500,
    when the email relay is down."""

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_returns_503_with_error_envelope(self, api_client, create_user, monkeypatch):
        create_user(email="user@example.com")

        def boom(**kwargs):
            raise SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        monkeypatch.setattr("bodepontoio.emails._django_send_mail", boom)

        response = api_client.post("/auth/login/", {"email": "user@example.com"})

        assert response.status_code == 503
        assert response.data["success"] is False
        assert response.data["type"] == "email_delivery_error"

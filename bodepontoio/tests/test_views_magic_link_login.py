import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings

from bodepontoio.tokens import make_login_token, make_uid

MAGIC_LINK_STRATEGY = {"LOGIN_STRATEGY": "magic_link"}


@pytest.mark.django_db
class TestLoginMagicLinkRequest:
    """POST login/ when LOGIN_STRATEGY = "magic_link" sends a magic link instead of checking a password."""

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_sends_magic_link_email(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "user@example.com" in mail.outbox[0].to

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_email_body_contains_login_url(self, api_client, create_user):
        user = create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        uid = make_uid(user)
        assert uid in mail.outbox[0].body
        assert "/login/magic/" in mail.outbox[0].body

    @override_settings(BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_AUTO_SIGNUP": True})
    def test_unknown_email_creates_user_and_sends_link(self, api_client):
        User = get_user_model()
        response = api_client.post("/auth/login/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert User.objects.filter(email="nobody@example.com").exists()
        assert len(mail.outbox) == 1
        assert "nobody@example.com" in mail.outbox[0].to

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_next_param_embedded_in_link(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "next": "/dashboard"},
        )
        assert "?next=/dashboard" in mail.outbox[0].body

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_next_param_url_encoded(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "next": "/team?id=42&tab=members"},
        )
        assert "?next=/team%3Fid%3D42%26tab%3Dmembers" in mail.outbox[0].body

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_omitted_next_no_query_string(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        assert "?next=" not in mail.outbox[0].body

    @pytest.mark.parametrize(
        "bad_next",
        [
            "https://evil.example.com/steal",
            "//evil.example.com/steal",
            "javascript:alert(1)",
            "dashboard",
            "\\\\evil.example.com",
        ],
    )
    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_invalid_next_rejected(self, api_client, create_user, bad_next):
        create_user(email="user@example.com")
        response = api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "next": bad_next},
        )
        assert response.status_code == 400
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_AUTO_SIGNUP": False})
    def test_auto_signup_disabled_unknown_email_no_user_no_email(self, api_client):
        User = get_user_model()
        response = api_client.post("/auth/login/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert not User.objects.filter(email="nobody@example.com").exists()
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_AUTO_SIGNUP": False})
    def test_auto_signup_disabled_known_email_still_sends_link(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 1

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_inactive_user_no_email(self, api_client, create_user):
        user = create_user(email="inactive@example.com")
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post("/auth/login/", {"email": "inactive@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    @override_settings(
        BODEPONTOIO={
            **MAGIC_LINK_STRATEGY,
            "LOGIN_AUTO_SIGNUP": True,
            "LOGIN_THROTTLE_IP_RATE": "2/min",
            "LOGIN_THROTTLE_EMAIL_RATE": None,
        }
    )
    def test_ip_throttle_blocks_auto_signup_flood(self, api_client):
        for i in range(2):
            response = api_client.post("/auth/login/", {"email": f"new{i}@example.com"})
            assert response.status_code == 200
        response = api_client.post("/auth/login/", {"email": "new2@example.com"})
        assert response.status_code == 429

    @override_settings(
        BODEPONTOIO={
            **MAGIC_LINK_STRATEGY,
            "LOGIN_THROTTLE_IP_RATE": None,
            "LOGIN_THROTTLE_EMAIL_RATE": "2/min",
        }
    )
    def test_email_throttle_blocks_repeated_requests(self, api_client, create_user):
        create_user(email="user@example.com")
        for _ in range(2):
            response = api_client.post("/auth/login/", {"email": "user@example.com"})
            assert response.status_code == 200
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 429


@pytest.mark.django_db
class TestLoginMagicLinkResend:
    """POST login/resend/ reissues a fresh magic link without auto-signup."""

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_resend_sends_new_link(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert "link" in response.data
        assert len(mail.outbox) == 1
        assert "/login/magic/" in mail.outbox[0].body

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_resend_unknown_email_no_email(self, api_client):
        response = api_client.post("/auth/login/resend/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_AUTO_SIGNUP": True})
    def test_resend_does_not_auto_signup(self, api_client):
        User = get_user_model()
        response = api_client.post("/auth/login/resend/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert not User.objects.filter(email="nobody@example.com").exists()
        assert len(mail.outbox) == 0

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_resend_inactive_user_no_email(self, api_client, create_user):
        user = create_user(email="inactive@example.com")
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post("/auth/login/resend/", {"email": "inactive@example.com"})
        assert response.status_code == 200
        assert len(mail.outbox) == 0

    def test_resend_returns_404_when_strategy_is_password(self, api_client, create_user):
        create_user(email="user@example.com")
        response = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert response.status_code == 404

    @override_settings(
        BODEPONTOIO={
            **MAGIC_LINK_STRATEGY,
            "LOGIN_THROTTLE_IP_RATE": None,
            "LOGIN_THROTTLE_EMAIL_RATE": "2/min",
        }
    )
    def test_resend_shares_email_throttle_with_login(self, api_client, create_user):
        create_user(email="user@example.com")
        first = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert first.status_code == 200
        second = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert second.status_code == 200
        third = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert third.status_code == 429


@pytest.mark.django_db
class TestLoginMagicLinkConfirm:
    """POST login/magic/confirm/ exchanges a valid uid+token for JWT tokens."""

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_success_returns_tokens(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_auto_verifies_email(self, api_client, create_user):
        user = create_user(email="unverified@example.com", is_email_verified=False)
        api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        user.auth.refresh_from_db()
        assert user.auth.is_email_verified is True

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_invalid_token(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": "bogus-token"},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_tampered_uid(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        token = make_login_token(user)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": "ZGVhZGJlZWY=", "token": token},
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_link_is_single_use(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert first.status_code == 200
        second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert second.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_inactive_user(self, api_client, create_user):
        user = create_user(email="inactive@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": uid, "token": token},
        )
        assert response.status_code == 401

    def test_returns_404_when_strategy_is_not_magic_link(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        assert response.status_code == 404

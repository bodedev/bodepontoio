from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.signals import user_logged_in
from django.core import mail
from django.test import override_settings

from bodepontoio.tokens import (
    login_token_generator,
    login_token_reuse_window,
    make_login_token,
    make_uid,
)

MAGIC_LINK_STRATEGY = {"LOGIN_STRATEGY": "magic_link"}
REUSE_STRATEGY = {
    **MAGIC_LINK_STRATEGY,
    "LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS": 900,
}


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

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_email_states_expiry_in_hours_by_default(self, api_client, create_user):
        """Django templates swallow unknown variables, so a typo in the expiry
        context would ship "expira em  minutos" with nothing failing."""
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        html = mail.outbox[0].alternatives[0][0]
        assert "expira em 72 horas" in html

    @override_settings(BODEPONTOIO=REUSE_STRATEGY)
    def test_email_states_expiry_in_minutes_with_a_window(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        html = mail.outbox[0].alternatives[0][0]
        assert "expira em 15 minutos" in html

    @override_settings(
        BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS": 5400}
    )
    def test_email_rounds_expiry_up_and_keeps_minutes_under_two_hours(
        self, api_client, create_user
    ):
        """A 90-minute window announced as "1 hora" would send users away 30
        minutes early. Never promise less time than the link has."""
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        html = mail.outbox[0].alternatives[0][0]
        assert "expira em 90 minutos" in html

    @override_settings(
        BODEPONTOIO={**MAGIC_LINK_STRATEGY, "LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS": 9000}
    )
    def test_email_rounds_partial_hours_up(self, api_client, create_user):
        create_user(email="user@example.com")
        api_client.post("/auth/login/", {"email": "user@example.com"})
        html = mail.outbox[0].alternatives[0][0]
        assert "expira em 3 horas" in html

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
            "/\t//evil.example.com",
            "/\r/evil.example.com",
            "/\n/evil.example.com",
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
    def test_link_is_single_use_by_default(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert first.status_code == 200
        second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert second.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_default_hash_matches_django(self, api_client, create_user):
        """Without a window the hash is Django's, so links issued by earlier
        versions keep working."""
        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        user = create_user(email="user@example.com", is_email_verified=True)
        legacy = PasswordResetTokenGenerator()
        legacy.key_salt = login_token_generator.key_salt
        # Pin the timestamp: two make_token() calls read the clock separately and
        # would disagree whenever the second ticks between them. Uses Django
        # private API, so this breaks if PasswordResetTokenGenerator internals
        # change; it guards the backward-compatibility claim, keep it working.
        ts = login_token_generator._num_seconds(login_token_generator._now())
        assert legacy._make_token_with_timestamp(
            user, ts, legacy.secret
        ) == login_token_generator._make_token_with_timestamp(
            user, ts, login_token_generator.secret
        )

    @override_settings(
        BODEPONTOIO={
            **MAGIC_LINK_STRATEGY,
            "LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS": None,
        }
    )
    def test_none_window_is_treated_as_off(self, api_client, create_user):
        """None must mean single-use, not blow up: other settings here take None
        for "off", and min() would raise from inside make_token."""
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert first.status_code == 200
        second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert second.status_code == 400

    @override_settings(
        BODEPONTOIO={
            **MAGIC_LINK_STRATEGY,
            "LOGIN_MAGIC_LINK_REUSE_WINDOW_SECONDS": -900,
        }
    )
    def test_negative_window_is_treated_as_off(self, api_client, create_user):
        """A negative window used to read as "window on" while the elapsed-time
        check compared against a negative bound, so every link failed with
        nothing to explain it. It must clamp to single-use instead."""
        assert login_token_reuse_window() == 0
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert first.status_code == 200
        second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert second.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_confirm_records_last_login(self, api_client, create_user):
        """The view stopped writing last_login itself; projects that read it
        should not notice."""
        user = create_user(email="user@example.com", is_email_verified=True)
        assert user.last_login is None
        api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        user.refresh_from_db()
        assert user.last_login is not None

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_single_use_survives_a_disconnected_update_last_login(
        self, api_client, create_user
    ):
        """Single-use rides on last_login moving, and Django's receiver is what
        normally moves it. A project that disconnects it would lose the
        guarantee silently, with no window configured and no error."""
        user_logged_in.disconnect(dispatch_uid="update_last_login")
        try:
            user = create_user(email="user@example.com", is_email_verified=True)
            uid = make_uid(user)
            token = make_login_token(user)
            first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
            assert first.status_code == 200
            second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
            assert second.status_code == 400
        finally:
            user_logged_in.connect(update_last_login, dispatch_uid="update_last_login")

    @override_settings(BODEPONTOIO=REUSE_STRATEGY)
    def test_link_can_be_reused_within_window(self, api_client, create_user):
        """Something burns the link first; the user's redemption must still work."""
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        first = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert first.status_code == 200
        second = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert second.status_code == 200

    @override_settings(BODEPONTOIO=REUSE_STRATEGY)
    def test_login_does_not_invalidate_other_pending_links(
        self, api_client, create_user, monkeypatch
    ):
        """Redeeming one link must not kill the user's other pending links."""
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)

        earlier = datetime.now() - timedelta(seconds=120)
        monkeypatch.setattr(login_token_generator, "_now", lambda: earlier)
        older_token = make_login_token(user)
        monkeypatch.undo()
        newer_token = make_login_token(user)
        assert older_token != newer_token

        for token in (newer_token, older_token):
            response = api_client.post(
                "/auth/login/magic/confirm/", {"uid": uid, "token": token}
            )
            assert response.status_code == 200

    @override_settings(BODEPONTOIO=REUSE_STRATEGY)
    def test_link_expires_after_window(self, api_client, create_user, monkeypatch):
        user = create_user(email="user@example.com", is_email_verified=True)
        stale = datetime.now() - timedelta(seconds=login_token_reuse_window() + 60)
        monkeypatch.setattr(login_token_generator, "_now", lambda: stale)
        token = make_login_token(user)
        monkeypatch.undo()
        response = api_client.post(
            "/auth/login/magic/confirm/", {"uid": make_uid(user), "token": token}
        )
        assert response.status_code == 400

    @override_settings(BODEPONTOIO=MAGIC_LINK_STRATEGY)
    def test_password_change_invalidates_pending_link(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        uid = make_uid(user)
        token = make_login_token(user)
        user.set_password("uma-senha-nova")
        user.save(update_fields=["password"])
        response = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert response.status_code == 400

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

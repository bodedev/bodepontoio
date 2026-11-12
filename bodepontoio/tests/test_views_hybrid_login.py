import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from bodepontoio.tokens import make_login_token, make_reset_token, make_uid

HYBRID = {"LOGIN_STRATEGY": "password_or_magic_link"}
HYBRID_SIGNUP = {**HYBRID, "LOGIN_AUTO_SIGNUP": True}


@pytest.fixture
def hybrid(settings):
    settings.BODEPONTOIO = HYBRID


@pytest.fixture
def plain_magic_link(settings):
    settings.BODEPONTOIO = {"LOGIN_STRATEGY": "magic_link"}


@pytest.fixture
def passwordless_user(create_user):
    """An account as passwordless signup leaves it: no usable password."""

    def _make(email="user@example.com", **kwargs):
        user = create_user(email=email, is_email_verified=True, **kwargs)
        user.set_unusable_password()
        user.save()
        return user

    return _make


@pytest.mark.django_db
@pytest.mark.usefixtures("hybrid")
class TestHybridLoginMethod:
    """POST login/ with only an email tells which method the account uses."""

    def test_account_with_password_answers_password_and_sends_nothing(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert response.data == {"method": "password"}
        assert mail.outbox == []

    def test_email_lookup_ignores_case(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/", {"email": "USER@example.com"})
        assert response.data == {"method": "password"}

    def test_passwordless_account_gets_magic_link(self, api_client, passwordless_user):
        user = passwordless_user()
        response = api_client.post("/auth/login/", {"email": "user@example.com", "next": "/membros"})
        assert response.status_code == 200
        assert response.data["method"] == "magic_link"
        assert len(mail.outbox) == 1
        assert make_uid(user) in mail.outbox[0].body
        assert "/login/magic/" in mail.outbox[0].body
        assert "next=/membros" in mail.outbox[0].body

    def test_unknown_email_without_auto_signup_answers_magic_link_silently(self, api_client, db):
        response = api_client.post("/auth/login/", {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert response.data["method"] == "magic_link"
        assert mail.outbox == []
        assert not get_user_model().objects.filter(email="nobody@example.com").exists()

    @override_settings(BODEPONTOIO=HYBRID_SIGNUP)
    def test_unknown_email_with_auto_signup_creates_passwordless_account(self, api_client, db):
        response = api_client.post("/auth/login/", {"email": "new@example.com"})
        assert response.data["method"] == "magic_link"
        assert len(mail.outbox) == 1
        user = get_user_model().objects.get(email="new@example.com")
        assert not user.has_usable_password()

    def test_inactive_passwordless_account_gets_no_email(self, api_client, passwordless_user):
        passwordless_user(is_active=False)
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.data["method"] == "magic_link"
        assert mail.outbox == []

    def test_invalid_email_is_rejected(self, api_client, db):
        response = api_client.post("/auth/login/", {"email": "not-an-email"})
        assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.usefixtures("hybrid")
class TestHybridPasswordLogin:
    def test_correct_password_returns_tokens(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["has_password"] is True
        assert mail.outbox == []

    def test_password_login_records_last_login(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        assert user.last_login is None
        api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "password": "testpassword123"},
        )
        user.refresh_from_db()
        assert user.last_login is not None

    def test_wrong_password_is_rejected(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/", {"email": "user@example.com", "password": "wrong-password"})
        assert response.status_code == 400
        assert "access" not in response.data

    def test_passwordless_account_cannot_log_in_with_any_password(self, api_client, passwordless_user):
        passwordless_user()
        response = api_client.post("/auth/login/", {"email": "user@example.com", "password": "whatever123"})
        assert response.status_code == 400
        assert mail.outbox == []

    def test_inactive_account_is_rejected(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True, is_active=False)
        response = api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 400
        assert "access" not in response.data


@pytest.mark.django_db
@pytest.mark.usefixtures("hybrid")
class TestHybridMagicLinkConfirm:
    def test_passwordless_account_logs_in_with_link(self, api_client, passwordless_user):
        user = passwordless_user()
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert response.data["user"]["has_password"] is False

    def test_link_dies_when_password_is_set(self, api_client, passwordless_user):
        user = passwordless_user()
        uid, token = make_uid(user), make_login_token(user)
        user.set_password("brand-new-pass-1")
        user.save()
        response = api_client.post("/auth/login/magic/confirm/", {"uid": uid, "token": token})
        assert response.status_code == 400

    def test_account_with_password_cannot_use_a_valid_link(self, api_client, create_user):
        """A link minted for the current password hash still verifies, so the
        view has to refuse it on its own."""
        user = create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        assert response.status_code == 400
        assert "access" not in response.data


@pytest.mark.django_db
@pytest.mark.usefixtures("hybrid")
class TestHybridLoginResend:
    def test_account_with_password_gets_no_link(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert response.status_code == 200
        assert response.data == {"method": "password"}
        assert mail.outbox == []

    def test_passwordless_account_gets_link(self, api_client, passwordless_user):
        passwordless_user()
        response = api_client.post("/auth/login/resend/", {"email": "user@example.com"})
        assert response.data["method"] == "magic_link"
        assert len(mail.outbox) == 1

    @override_settings(BODEPONTOIO=HYBRID_SIGNUP)
    def test_never_creates_accounts(self, api_client, db):
        response = api_client.post("/auth/login/resend/", {"email": "new@example.com"})
        assert response.data["method"] == "magic_link"
        assert mail.outbox == []
        assert not get_user_model().objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
class TestPasswordSetView:
    def test_passwordless_account_sets_first_password(self, api_client, passwordless_user):
        user = passwordless_user()
        api_client.force_authenticate(user=user)
        response = api_client.post("/auth/password/set/", {"new_password": "brand-new-pass-1"})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("brand-new-pass-1")

    def test_refused_when_account_already_has_password(self, auth_client):
        client, user = auth_client
        response = client.post("/auth/password/set/", {"new_password": "brand-new-pass-1"})
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password("testpassword123")

    def test_second_call_is_refused(self, api_client, passwordless_user):
        user = passwordless_user()
        api_client.force_authenticate(user=user)
        api_client.post("/auth/password/set/", {"new_password": "brand-new-pass-1"})
        response = api_client.post("/auth/password/set/", {"new_password": "another-pass-22"})
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password("brand-new-pass-1")

    def test_too_short_is_rejected(self, api_client, passwordless_user):
        user = passwordless_user()
        api_client.force_authenticate(user=user)
        response = api_client.post("/auth/password/set/", {"new_password": "short"})
        assert response.status_code == 400
        user.refresh_from_db()
        assert not user.has_usable_password()

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}]
    )
    def test_runs_django_password_validators(self, api_client, passwordless_user):
        user = passwordless_user()
        api_client.force_authenticate(user=user)
        response = api_client.post("/auth/password/set/", {"new_password": "password123"})
        assert response.status_code == 400
        user.refresh_from_db()
        assert not user.has_usable_password()

    def test_unauthenticated(self, api_client, db):
        response = api_client.post("/auth/password/set/", {"new_password": "brand-new-pass-1"})
        assert response.status_code == 401

    @override_settings(BODEPONTOIO=HYBRID)
    def test_full_flow_then_password_login(self, api_client, passwordless_user):
        user = passwordless_user()
        api_client.force_authenticate(user=user)
        api_client.post("/auth/password/set/", {"new_password": "brand-new-pass-1"})

        anonymous = APIClient()
        method = anonymous.post("/auth/login/", {"email": "user@example.com"})
        assert method.data == {"method": "password"}
        login = anonymous.post(
            "/auth/login/",
            {"email": "user@example.com", "password": "brand-new-pass-1"},
        )
        assert login.status_code == 200
        assert "access" in login.data


@pytest.mark.django_db
class TestPasswordResetMarksEmailVerified:
    def _reset(self, api_client, user):
        return api_client.post(
            "/auth/password/reset/confirm/",
            {
                "uid": make_uid(user),
                "token": make_reset_token(user),
                "new_password": "brand-new-pass-1",
            },
        )

    @override_settings(BODEPONTOIO=HYBRID)
    def test_hybrid_reset_verifies_email_so_password_login_works(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=False)
        user.set_unusable_password()
        user.save()
        assert self._reset(api_client, user).status_code == 200
        user.auth.refresh_from_db()
        assert user.auth.is_email_verified

        login = api_client.post(
            "/auth/login/",
            {"email": "user@example.com", "password": "brand-new-pass-1"},
        )
        assert login.status_code == 200

    def test_other_strategies_leave_verification_alone(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=False)
        assert self._reset(api_client, user).status_code == 200
        user.auth.refresh_from_db()
        assert not user.auth.is_email_verified


@pytest.mark.django_db
@pytest.mark.usefixtures("plain_magic_link")
class TestMagicLinkStrategyUnchanged:
    """The plain magic_link strategy keeps its old string response and keeps
    accepting links for accounts that happen to have a password."""

    def test_login_still_answers_a_string(self, api_client, create_user):
        create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post("/auth/login/", {"email": "user@example.com"})
        assert response.data == "Um link de acesso foi enviado para o seu e-mail."
        assert len(mail.outbox) == 1

    def test_account_with_password_can_still_use_link(self, api_client, create_user):
        user = create_user(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            "/auth/login/magic/confirm/",
            {"uid": make_uid(user), "token": make_login_token(user)},
        )
        assert response.status_code == 200

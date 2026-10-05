from io import StringIO
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.state import ProjectState
from django.test import override_settings

from bodepontoio.models import OTPCode
from bodepontoio.operations import DEFAULT_INDEX_NAME, AddUniqueEmailIndex
from bodepontoio.otp import generate_otp
from bodepontoio.users import (
    get_or_create_user_by_email,
    get_user_by_email,
    normalize_email,
)

User = get_user_model()

GOOGLE_MOCK_TARGET = "bodepontoio.serializers.google_id_token.verify_oauth2_token"


def _apply(operation, forwards=True):
    state = ProjectState.from_apps(apps)
    with connection.schema_editor() as editor:
        if forwards:
            operation.database_forwards("bodepontoio", editor, state, state)
        else:
            operation.database_backwards("bodepontoio", editor, state, state)


@pytest.fixture
def unique_email_index(transactional_db):
    """Cria o índice único de e-mail e o remove no fim (o flush do teste não desfaz DDL)."""
    operation = AddUniqueEmailIndex()
    _apply(operation)
    yield operation
    _apply(operation, forwards=False)


def _register(api_client, email, password="testpassword123"):
    return api_client.post("/auth/register/", {"email": email, "password": password})


class TestNormalizeEmail:
    def test_lowercases_whole_address_and_strips(self):
        assert normalize_email("  MARIAFPS@SebraeSP.com.br ") == "mariafps@sebraesp.com.br"

    def test_empty(self):
        assert normalize_email(None) == ""
        assert normalize_email("") == ""


@pytest.mark.django_db
class TestGetUserByEmail:
    def test_ignores_case(self, create_user):
        user = create_user(email="Fulano@Example.com")
        assert get_user_by_email("fulano@example.COM") == user

    def test_unknown_or_empty_email(self, create_user):
        create_user(email="", username="sem-email")
        assert get_user_by_email("nobody@example.com") is None
        assert get_user_by_email("") is None

    def test_legacy_duplicates_return_oldest(self, create_user):
        oldest = create_user(email="Dup@example.com", username="dup-a")
        create_user(email="dup@example.com", username="dup-b")
        assert get_user_by_email("DUP@example.com") == oldest


@pytest.mark.django_db
class TestRegister:
    def test_stores_email_lowercased(self, api_client):
        response = _register(api_client, "  Novo.Usuario@Example.com ")
        assert response.status_code == 201
        user = User.objects.get()
        assert user.email == "novo.usuario@example.com"
        assert user.username == "novo.usuario"
        assert user.check_password("testpassword123")

    def test_rejects_same_email_in_other_case(self, api_client, create_user):
        create_user(email="Fulano@example.com")
        response = _register(api_client, "fulano@EXAMPLE.com")
        assert response.status_code == 400
        assert User.objects.count() == 1


@pytest.mark.django_db
class TestPasswordLogin:
    def test_login_with_email_in_other_case(self, api_client, create_user):
        create_user(email="Login@Example.com", password="testpassword123", is_email_verified=True)
        response = api_client.post("/auth/login/", {"login": "login@example.com", "password": "testpassword123"})
        assert response.status_code == 200
        assert "access" in response.data

    def test_login_with_legacy_duplicates_does_not_crash(self, api_client, create_user):
        create_user(email="dup@example.com", username="dup-a", password="testpassword123", is_email_verified=True)
        create_user(email="DUP@example.com", username="dup-b", password="outrasenha123", is_email_verified=True)
        response = api_client.post("/auth/login/", {"login": "Dup@example.com", "password": "testpassword123"})
        assert response.status_code == 200


OTP_STRATEGY = {"LOGIN_STRATEGY": "otp", "LOGIN_AUTO_SIGNUP": True}


@pytest.mark.django_db
class TestPasswordlessLogin:
    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_other_case_reuses_existing_account(self, api_client, create_user):
        user = create_user(email="Fulano.Teste@Example.com")
        response = api_client.post("/auth/login/", {"email": "fulano.teste@example.com"})
        assert response.status_code == 200
        assert User.objects.count() == 1
        assert mail.outbox[0].to == [user.email]

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_auto_signup_stores_email_lowercased(self, api_client):
        api_client.post("/auth/login/", {"email": "MARIAFPS@sebraesp.com.br"})
        assert User.objects.get().email == "mariafps@sebraesp.com.br"

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_confirm_with_email_in_other_case(self, api_client, create_user):
        user = create_user(email="Otp@Example.com")
        otp = generate_otp(user, OTPCode.Purpose.LOGIN)
        response = api_client.post("/auth/login/otp/confirm/", {"email": "otp@example.com", "code": otp.code})
        assert response.status_code == 200
        assert "access" in response.data

    @override_settings(BODEPONTOIO=OTP_STRATEGY)
    def test_resend_with_email_in_other_case(self, api_client, create_user):
        create_user(email="Resend@Example.com")
        api_client.post("/auth/login/resend/", {"email": "resend@example.com"})
        assert len(mail.outbox) == 1


@pytest.mark.django_db
class TestEmailLookupsIgnoreCase:
    def test_password_reset_request(self, api_client, create_user):
        create_user(email="Reset@Example.com")
        api_client.post("/auth/password/reset/", {"email": "reset@example.com"})
        assert len(mail.outbox) == 1

    def test_resend_email_confirmation(self, api_client, create_user):
        create_user(email="Confirm@Example.com")
        api_client.post("/auth/email/confirm/resend/", {"email": "confirm@example.com"})
        assert len(mail.outbox) == 1

    def test_google_login_reuses_account_in_other_case(self, api_client, create_user):
        user = create_user(email="Google@Example.com")
        info = {"email": "google@example.com", "given_name": "G", "family_name": "U"}
        with patch(GOOGLE_MOCK_TARGET, return_value=info):
            response = api_client.post("/auth/social/google/", {"id_token": "t"}, format="json")
        assert response.status_code == 200
        assert list(User.objects.values_list("pk", flat=True)) == [user.pk]


@pytest.mark.django_db
class TestUsernameCollisionRetry:
    def test_retries_with_new_username(self, create_user):
        create_user(email="other@example.com", username="taken")
        with patch("bodepontoio.users.unique_username_for_email", side_effect=["taken", "free"]):
            user, created = get_or_create_user_by_email("new@example.com")
        assert created
        assert user.username == "free"


class TestConcurrentSignupWithIndex:
    """Simula a segunda de duas requisições simultâneas: ela passou pela checagem de
    e-mail antes de a primeira gravar, e só o índice único a impede de criar a conta."""

    def test_passwordless_signup_returns_existing_user(self, unique_email_index, create_user):
        existing = create_user(email="MARIAFPS@sebraesp.com.br", username="MARIAFPS")
        with patch("bodepontoio.users.get_user_by_email", side_effect=[None, existing]):
            user, created = get_or_create_user_by_email("MARIAFPS@sebraesp.com.br")
        assert not created
        assert user == existing
        assert User.objects.count() == 1

    def test_register_reports_email_taken(self, unique_email_index, api_client, create_user):
        create_user(email="MARIAFPS@sebraesp.com.br", username="MARIAFPS")
        with patch("bodepontoio.serializers.get_user_by_email", return_value=None):
            response = _register(api_client, "MARIAFPS@sebraesp.com.br")
        assert response.status_code == 400
        assert User.objects.count() == 1


class TestAddUniqueEmailIndex:
    def test_blocks_same_email_in_other_case(self, unique_email_index):
        User.objects.create(username="a", email="fulano@example.com")
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create(username="b", email="Fulano@Example.com")

    def test_allows_many_users_without_email(self, unique_email_index):
        User.objects.create(username="a", email="")
        User.objects.create(username="b", email="")
        assert User.objects.filter(email="").count() == 2

    def test_backwards_removes_index(self, transactional_db):
        operation = AddUniqueEmailIndex()
        _apply(operation)
        _apply(operation, forwards=False)
        User.objects.create(username="a", email="x@example.com")
        User.objects.create(username="b", email="X@example.com")
        assert User.objects.count() == 2

    def test_refuses_when_duplicates_exist(self, transactional_db):
        User.objects.create(username="a", email="dup@example.com")
        User.objects.create(username="b", email="DUP@example.com")
        with pytest.raises(ValueError, match="bpio_emails_duplicados"):
            _apply(AddUniqueEmailIndex())
        # Nada foi criado: ainda dá para inserir outra variação.
        User.objects.create(username="c", email="Dup@example.com")

    def test_deconstruct_defaults(self):
        assert AddUniqueEmailIndex().deconstruct() == ("AddUniqueEmailIndex", [], {})
        assert AddUniqueEmailIndex(name="outro").deconstruct() == ("AddUniqueEmailIndex", [], {"name": "outro"})
        assert DEFAULT_INDEX_NAME in AddUniqueEmailIndex().describe()


@pytest.mark.django_db
class TestDuplicateEmailsCommand:
    def test_lists_groups(self, create_user):
        create_user(email="MARIAFPS@sebraesp.com.br", username="MARIAFPS")
        create_user(email="mariafps@sebraesp.com.br", username="MARIAFPS1")
        create_user(email="unico@example.com", username="unico")
        out = StringIO()
        call_command("bpio_emails_duplicados", stdout=out)
        output = out.getvalue()
        assert "mariafps@sebraesp.com.br (2 usuários)" in output
        assert "'MARIAFPS1'" in output
        assert "unico" not in output

    def test_nothing_to_report(self, create_user):
        create_user(email="unico@example.com")
        out = StringIO()
        call_command("bpio_emails_duplicados", stdout=out)
        assert "Nenhum e-mail duplicado" in out.getvalue()

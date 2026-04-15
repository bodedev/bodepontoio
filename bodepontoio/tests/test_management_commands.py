from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from bodepontoio.models import UserAuth


@pytest.mark.django_db
class TestBpioCriarUserAuth:
    def test_creates_userauth_for_users_without_one(self, create_user):
        user1 = create_user(email="u1@example.com")
        user2 = create_user(email="u2@example.com", username="u2")
        UserAuth.objects.filter(user__in=[user1, user2]).delete()
        assert UserAuth.objects.filter(user__in=[user1, user2]).count() == 0

        call_command("bpio_criar_userauth")

        assert UserAuth.objects.filter(user=user1, is_email_verified=True).exists()
        assert UserAuth.objects.filter(user=user2, is_email_verified=True).exists()

    def test_does_not_duplicate_existing_userauth(self, create_user):
        user = create_user(email="existing@example.com")
        assert UserAuth.objects.filter(user=user).count() == 1

        call_command("bpio_criar_userauth")

        assert UserAuth.objects.filter(user=user).count() == 1

    def test_no_op_when_no_users_without_auth(self, create_user):
        create_user(email="u@example.com")
        out = StringIO()

        call_command("bpio_criar_userauth", stdout=out)

        assert "Nenhum usuário sem UserAuth encontrado." in out.getvalue()

    def test_reports_count_of_created(self, create_user):
        user1 = create_user(email="u1@example.com")
        user2 = create_user(email="u2@example.com", username="u2")
        UserAuth.objects.filter(user__in=[user1, user2]).delete()
        out = StringIO()

        call_command("bpio_criar_userauth", stdout=out)

        assert "2 UserAuth(s) criado(s) com sucesso." in out.getvalue()



class TestBpioImportarPaises(SimpleTestCase):

    @patch('bodepontoio.management.commands.bpio_importar_paises.Pais')
    @patch('builtins.open')
    def test_outputs_to_stdout(self, mock_open, mock_pais):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: None
        mock_pais.objects.get_or_create.return_value = (mock_pais, True)

        out = StringIO()
        with patch('csv.DictReader', return_value=[{
            'País': 'Brasil', 'Capital': 'Brasília',
            '3 letras': 'BRA', '2 letras': 'BR',
        }]):
            call_command('bpio_importar_paises', stdout=out)

        output = out.getvalue()
        self.assertIn('Fim de processo!', output)


class TestCompressImagesWithTinify(SimpleTestCase):

    @override_settings()
    def test_missing_tinypng_key_shows_error(self):
        from django.conf import settings
        if hasattr(settings, 'TINYPNG_KEY'):
            delattr(settings, 'TINYPNG_KEY')

        err = StringIO()
        call_command('compress-images-with-tinify', '--folders', '/tmp', stderr=err)
        self.assertIn('TINYPNG_KEY', err.getvalue())

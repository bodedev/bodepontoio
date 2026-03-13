from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


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

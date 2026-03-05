from unittest.mock import MagicMock

from django.test import SimpleTestCase

from bodepontoio.utils.cleaners import (
    extract_name_and_surname,
    file_extension,
    file_name_cleaner,
    get_client_ip,
)


class TestFileNameCleaner(SimpleTestCase):

    def test_removes_special_characters(self):
        result = file_name_cleaner("Relatório Mensal.pdf")
        self.assertEqual(result, "relatorio-mensal.pdf")

    def test_preserves_extension(self):
        result = file_name_cleaner("Arquivo Com Espaços.xlsx")
        self.assertEqual(result, "arquivo-com-espacos.xlsx")

    def test_handles_multiple_dots(self):
        result = file_name_cleaner("arquivo.backup.tar.gz")
        self.assertEqual(result, "arquivobackuptar.gz")

    def test_handles_accented_characters(self):
        result = file_name_cleaner("Prévia Orçamento.docx")
        self.assertEqual(result, "previa-orcamento.docx")

    def test_handles_uppercase(self):
        result = file_name_cleaner("DOCUMENTO IMPORTANTE.PDF")
        self.assertEqual(result, "documento-importante.PDF")


class TestFileExtension(SimpleTestCase):

    def test_returns_extension(self):
        result = file_extension("documento.pdf")
        self.assertEqual(result, ".pdf")

    def test_returns_extension_uppercase(self):
        result = file_extension("documento.PDF")
        self.assertEqual(result, ".PDF")

    def test_returns_empty_string_when_no_extension(self):
        result = file_extension("arquivo_sem_extensao")
        self.assertEqual(result, "")

    def test_returns_last_extension_only(self):
        result = file_extension("arquivo.tar.gz")
        self.assertEqual(result, ".gz")


class TestExtractNameAndSurname(SimpleTestCase):

    def test_extracts_name_and_surname(self):
        nome, sobrenome = extract_name_and_surname("João Silva")
        self.assertEqual(nome, "João")
        self.assertEqual(sobrenome, "Silva")

    def test_extracts_name_and_multiple_surnames(self):
        nome, sobrenome = extract_name_and_surname("Maria José da Silva")
        self.assertEqual(nome, "Maria")
        self.assertEqual(sobrenome, "José da Silva")

    def test_returns_none_for_single_word(self):
        nome, sobrenome = extract_name_and_surname("João")
        self.assertIsNone(nome)
        self.assertIsNone(sobrenome)

    def test_returns_none_for_empty_string(self):
        nome, sobrenome = extract_name_and_surname("")
        self.assertIsNone(nome)
        self.assertIsNone(sobrenome)

    def test_handles_extra_spaces(self):
        nome, sobrenome = extract_name_and_surname("  João   Silva  ")
        self.assertEqual(nome, "João")
        self.assertEqual(sobrenome, "Silva")


class TestGetClientIp(SimpleTestCase):

    def test_returns_ip_from_x_forwarded_for(self):
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "192.168.1.1, 10.0.0.1"}
        result = get_client_ip(request)
        self.assertEqual(result, "192.168.1.1")

    def test_returns_ip_from_remote_addr(self):
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.100"}
        result = get_client_ip(request)
        self.assertEqual(result, "192.168.1.100")

    def test_prefers_x_forwarded_for_over_remote_addr(self):
        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "192.168.1.1",
            "REMOTE_ADDR": "10.0.0.1",
        }
        result = get_client_ip(request)
        self.assertEqual(result, "192.168.1.1")

    def test_returns_none_when_no_ip_available(self):
        request = MagicMock()
        request.META = {}
        result = get_client_ip(request)
        self.assertIsNone(result)

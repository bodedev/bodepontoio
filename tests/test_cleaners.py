from unittest.mock import MagicMock

from bodepontoio.utils.cleaners import (
    extract_name_and_surname,
    file_extension,
    file_name_cleaner,
    get_client_ip,
)


class TestFileNameCleaner:
    def test_removes_special_characters(self):
        assert file_name_cleaner("Relatório Mensal.pdf") == "relatorio-mensal.pdf"

    def test_preserves_extension(self):
        assert file_name_cleaner("Arquivo Com Espaços.xlsx") == "arquivo-com-espacos.xlsx"

    def test_handles_multiple_dots(self):
        assert file_name_cleaner("arquivo.backup.tar.gz") == "arquivobackuptar.gz"

    def test_handles_accented_characters(self):
        assert file_name_cleaner("Prévia Orçamento.docx") == "previa-orcamento.docx"

    def test_handles_uppercase(self):
        assert file_name_cleaner("DOCUMENTO IMPORTANTE.PDF") == "documento-importante.PDF"


class TestFileExtension:
    def test_returns_extension(self):
        assert file_extension("documento.pdf") == ".pdf"

    def test_returns_extension_uppercase(self):
        assert file_extension("documento.PDF") == ".PDF"

    def test_returns_empty_string_when_no_extension(self):
        assert file_extension("arquivo_sem_extensao") == ""

    def test_returns_last_extension_only(self):
        assert file_extension("arquivo.tar.gz") == ".gz"


class TestExtractNameAndSurname:
    def test_extracts_name_and_surname(self):
        nome, sobrenome = extract_name_and_surname("João Silva")
        assert nome == "João"
        assert sobrenome == "Silva"

    def test_extracts_name_and_multiple_surnames(self):
        nome, sobrenome = extract_name_and_surname("Maria José da Silva")
        assert nome == "Maria"
        assert sobrenome == "José da Silva"

    def test_returns_none_for_single_word(self):
        nome, sobrenome = extract_name_and_surname("João")
        assert nome is None
        assert sobrenome is None

    def test_returns_none_for_empty_string(self):
        nome, sobrenome = extract_name_and_surname("")
        assert nome is None
        assert sobrenome is None

    def test_handles_extra_spaces(self):
        nome, sobrenome = extract_name_and_surname("  João   Silva  ")
        assert nome == "João"
        assert sobrenome == "Silva"


class TestGetClientIp:
    def test_returns_ip_from_x_forwarded_for(self):
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "192.168.1.1, 10.0.0.1"}
        assert get_client_ip(request) == "192.168.1.1"

    def test_returns_ip_from_remote_addr(self):
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.100"}
        assert get_client_ip(request) == "192.168.1.100"

    def test_prefers_x_forwarded_for_over_remote_addr(self):
        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "192.168.1.1",
            "REMOTE_ADDR": "10.0.0.1",
        }
        assert get_client_ip(request) == "192.168.1.1"

    def test_returns_none_when_no_ip_available(self):
        request = MagicMock()
        request.META = {}
        assert get_client_ip(request) is None

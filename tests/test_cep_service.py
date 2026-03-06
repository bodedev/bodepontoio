from unittest.mock import MagicMock, patch

import pytest

from bodepontoio.models import ConsultaCEP
from bodepontoio.services.cep_service import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    CEPService,
    DadosCEP,
)


@pytest.mark.django_db
class TestCEPServiceValidacao:
    def setup_method(self):
        self.service = CEPService()

    def test_cep_invalido_muito_curto(self):
        with pytest.raises(CEPInvalidoError, match="CEP inválido"):
            self.service.consultar("123")

    def test_cep_invalido_muito_longo(self):
        with pytest.raises(CEPInvalidoError, match="CEP inválido"):
            self.service.consultar("123456789")

    def test_cep_invalido_com_letras(self):
        with pytest.raises(CEPInvalidoError, match="CEP inválido"):
            self.service.consultar("0100100A")

    def test_cep_invalido_vazio(self):
        with pytest.raises(CEPInvalidoError, match="CEP inválido"):
            self.service.consultar("")

    def test_limpar_cep_remove_hifen(self):
        assert self.service._limpar_cep("01001-000") == "01001000"

    def test_limpar_cep_remove_ponto(self):
        assert self.service._limpar_cep("01.001-000") == "01001000"

    def test_formatar_cep(self):
        assert self.service._formatar_cep("01001000") == "01001-000"


@pytest.mark.django_db
class TestCEPServiceCache:
    def setup_method(self):
        self.service = CEPService()
        self.cep_cache = ConsultaCEP.objects.create(
            cep="01001-000",
            logradouro="Praça da Sé",
            complemento="lado ímpar",
            bairro="Sé",
            localidade="São Paulo",
            uf="SP",
            ibge="3550308",
            ddd="11",
            localidade_slug="sao-paulo",
            fonte="viacep",
        )

    def test_consulta_retorna_do_cache(self):
        with patch.object(self.service, "_consultar_viacep") as mock_viacep:
            with patch.object(self.service, "_consultar_awesomeapi") as mock_awesome:
                resultado = self.service.consultar("01001000")
                mock_viacep.assert_not_called()
                mock_awesome.assert_not_called()
                assert resultado.cep == "01001-000"
                assert resultado.localidade == "São Paulo"
                assert resultado.fonte == "viacep"

    def test_consulta_cache_com_cep_formatado(self):
        with patch.object(self.service, "_consultar_viacep") as mock_viacep:
            resultado = self.service.consultar("01001-000")
            mock_viacep.assert_not_called()
            assert resultado.cep == "01001-000"


@pytest.mark.django_db
class TestCEPServiceViaCEP:
    def setup_method(self):
        self.service = CEPService()

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_sucesso(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "cep": "91920-130",
            "logradouro": "Rua Exemplo",
            "complemento": "",
            "bairro": "Centro",
            "localidade": "Porto Alegre",
            "uf": "RS",
            "ibge": "4314902",
            "ddd": "51",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        resultado = self.service.consultar("91920130")

        assert resultado.cep == "91920-130"
        assert resultado.localidade == "Porto Alegre"
        assert resultado.uf == "RS"
        assert resultado.localidade_slug == "porto-alegre"
        assert resultado.fonte == "viacep"

        consulta_salva = ConsultaCEP.objects.get(cep="91920-130")
        assert consulta_salva.localidade == "Porto Alegre"

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_cep_nao_encontrado(self, mock_get):
        mock_response_viacep = MagicMock()
        mock_response_viacep.json.return_value = {"erro": True}
        mock_response_viacep.raise_for_status = MagicMock()

        mock_response_awesome = MagicMock()
        mock_response_awesome.json.return_value = {
            "cep": "12345-678",
            "address": "Rua Fallback",
            "district": "Bairro",
            "city": "Cidade",
            "state": "XX",
            "city_ibge": "1234567",
            "ddd": "99",
        }
        mock_response_awesome.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_viacep, mock_response_awesome]

        resultado = self.service.consultar("12345678")
        assert resultado.fonte == "awesomeapi"
        assert resultado.localidade == "Cidade"

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_erro_string_faz_fallback(self, mock_get):
        mock_response_viacep = MagicMock()
        mock_response_viacep.json.return_value = {"erro": "true"}
        mock_response_viacep.raise_for_status = MagicMock()

        mock_response_awesome = MagicMock()
        mock_response_awesome.json.return_value = {
            "cep": "97500-140",
            "address": "Rua General Câmara",
            "district": "Centro",
            "city": "Uruguaiana",
            "state": "RS",
            "city_ibge": "4322400",
            "ddd": "55",
        }
        mock_response_awesome.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_viacep, mock_response_awesome]

        resultado = self.service.consultar("97500140")
        assert resultado.fonte == "awesomeapi"
        assert resultado.localidade == "Uruguaiana"
        assert resultado.uf == "RS"
        assert resultado.cep == "97500-140"


@pytest.mark.django_db
class TestCEPServiceAwesomeAPI:
    def setup_method(self):
        self.service = CEPService()

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_fallback_awesomeapi_quando_viacep_falha(self, mock_get):
        import requests

        mock_get.side_effect = [
            requests.RequestException("Erro de conexão"),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "cep": "91920-130",
                        "address": "Rua Fallback",
                        "district": "Centro",
                        "city": "Porto Alegre",
                        "state": "RS",
                        "city_ibge": "4314902",
                        "ddd": "51",
                    }
                ),
                raise_for_status=MagicMock(),
            ),
        ]

        resultado = self.service.consultar("91920130")
        assert resultado.fonte == "awesomeapi"
        assert resultado.localidade == "Porto Alegre"
        assert resultado.logradouro == "Rua Fallback"

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_cep_nao_encontrado_em_nenhum_provedor(self, mock_get):
        mock_response_viacep = MagicMock()
        mock_response_viacep.json.return_value = {"erro": True}
        mock_response_viacep.raise_for_status = MagicMock()

        mock_response_awesome = MagicMock()
        mock_response_awesome.json.return_value = {"status": 404}
        mock_response_awesome.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_viacep, mock_response_awesome]

        with pytest.raises(CEPNaoEncontradoError, match="00000-000"):
            self.service.consultar("00000000")

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_ambos_provedores_falham_com_excecao(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Erro de conexão")

        with pytest.raises(CEPNaoEncontradoError):
            self.service.consultar("91920130")


@pytest.mark.django_db
class TestCEPServiceBuscarPorSlug:
    def setup_method(self):
        self.service = CEPService()

    @pytest.fixture(autouse=True)
    def _setup_data(self):
        ConsultaCEP.objects.create(
            cep="91920-130", logradouro="Rua A", bairro="Centro",
            localidade="Porto Alegre", uf="RS", localidade_slug="porto-alegre", fonte="viacep",
        )
        ConsultaCEP.objects.create(
            cep="91920-140", logradouro="Rua B", bairro="Bairro X",
            localidade="Porto Alegre", uf="RS", localidade_slug="porto-alegre", fonte="viacep",
        )
        ConsultaCEP.objects.create(
            cep="01001-000", logradouro="Praça da Sé", bairro="Sé",
            localidade="São Paulo", uf="SP", localidade_slug="sao-paulo", fonte="viacep",
        )

    def test_buscar_por_slug_retorna_multiplos(self):
        resultado = self.service.buscar_por_slug("porto-alegre")
        assert len(resultado) == 2
        ceps = [r.cep for r in resultado]
        assert "91920-130" in ceps
        assert "91920-140" in ceps

    def test_buscar_por_slug_retorna_unico(self):
        resultado = self.service.buscar_por_slug("sao-paulo")
        assert len(resultado) == 1
        assert resultado[0].localidade == "São Paulo"

    def test_buscar_por_slug_nao_encontrado(self):
        resultado = self.service.buscar_por_slug("cidade-inexistente")
        assert len(resultado) == 0


class TestDadosCEP:
    def test_criacao_dados_cep(self):
        dados = DadosCEP(
            cep="01001-000", logradouro="Praça da Sé", complemento="lado ímpar",
            bairro="Sé", localidade="São Paulo", uf="SP", ibge="3550308",
            ddd="11", localidade_slug="sao-paulo", fonte="viacep",
        )
        assert dados.cep == "01001-000"
        assert dados.localidade == "São Paulo"
        assert dados.localidade_slug == "sao-paulo"


@pytest.mark.django_db
class TestConsultaCEPModel:
    def test_slug_gerado_automaticamente(self):
        consulta = ConsultaCEP.objects.create(
            cep="12345-678", logradouro="Rua Teste", bairro="Centro",
            localidade="São José dos Campos", uf="SP", fonte="viacep",
        )
        assert consulta.localidade_slug == "sao-jose-dos-campos"

    def test_slug_nao_sobrescreve_existente(self):
        consulta = ConsultaCEP.objects.create(
            cep="12345-678", logradouro="Rua Teste", bairro="Centro",
            localidade="São José dos Campos", uf="SP",
            localidade_slug="slug-customizado", fonte="viacep",
        )
        assert consulta.localidade_slug == "slug-customizado"

    def test_str_representation(self):
        consulta = ConsultaCEP.objects.create(
            cep="01001-000", logradouro="Praça da Sé", bairro="Sé",
            localidade="São Paulo", uf="SP", fonte="viacep",
        )
        assert str(consulta) == "01001-000 - São Paulo/SP"

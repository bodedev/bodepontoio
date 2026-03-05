"""Testes unitários para o serviço de consulta de CEP."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from bodepontoio.models import ConsultaCEP
from bodepontoio.services.cep_service import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    CEPService,
    DadosCEP,
)


class CEPServiceValidacaoTest(TestCase):
    """Testes de validação de CEP."""

    def setUp(self):
        self.service = CEPService()

    def test_cep_invalido_muito_curto(self):
        """CEP com menos de 8 dígitos deve lançar exceção."""
        with self.assertRaises(CEPInvalidoError) as context:
            self.service.consultar("123")
        self.assertIn("CEP inválido", str(context.exception))

    def test_cep_invalido_muito_longo(self):
        """CEP com mais de 8 dígitos deve lançar exceção."""
        with self.assertRaises(CEPInvalidoError) as context:
            self.service.consultar("123456789")
        self.assertIn("CEP inválido", str(context.exception))

    def test_cep_invalido_com_letras(self):
        """CEP com letras deve lançar exceção."""
        with self.assertRaises(CEPInvalidoError) as context:
            self.service.consultar("0100100A")
        self.assertIn("CEP inválido", str(context.exception))

    def test_cep_invalido_vazio(self):
        """CEP vazio deve lançar exceção."""
        with self.assertRaises(CEPInvalidoError) as context:
            self.service.consultar("")
        self.assertIn("CEP inválido", str(context.exception))

    def test_limpar_cep_remove_hifen(self):
        """Método _limpar_cep deve remover hífen."""
        resultado = self.service._limpar_cep("01001-000")
        self.assertEqual(resultado, "01001000")

    def test_limpar_cep_remove_ponto(self):
        """Método _limpar_cep deve remover ponto."""
        resultado = self.service._limpar_cep("01.001-000")
        self.assertEqual(resultado, "01001000")

    def test_formatar_cep(self):
        """Método _formatar_cep deve adicionar hífen."""
        resultado = self.service._formatar_cep("01001000")
        self.assertEqual(resultado, "01001-000")


class CEPServiceCacheTest(TestCase):
    """Testes de cache do banco de dados."""

    def setUp(self):
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
        """Consulta deve retornar dados do cache sem chamar APIs."""
        with patch.object(self.service, "_consultar_viacep") as mock_viacep:
            with patch.object(self.service, "_consultar_awesomeapi") as mock_awesome:
                resultado = self.service.consultar("01001000")

                mock_viacep.assert_not_called()
                mock_awesome.assert_not_called()
                self.assertEqual(resultado.cep, "01001-000")
                self.assertEqual(resultado.localidade, "São Paulo")
                self.assertEqual(resultado.fonte, "viacep")

    def test_consulta_cache_com_cep_formatado(self):
        """Consulta com CEP formatado deve encontrar no cache."""
        with patch.object(self.service, "_consultar_viacep") as mock_viacep:
            resultado = self.service.consultar("01001-000")

            mock_viacep.assert_not_called()
            self.assertEqual(resultado.cep, "01001-000")


class CEPServiceViaCEPTest(TestCase):
    """Testes de consulta ao ViaCEP."""

    def setUp(self):
        self.service = CEPService()

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_sucesso(self, mock_get):
        """Consulta bem-sucedida ao ViaCEP deve salvar no banco."""
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

        self.assertEqual(resultado.cep, "91920-130")
        self.assertEqual(resultado.localidade, "Porto Alegre")
        self.assertEqual(resultado.uf, "RS")
        self.assertEqual(resultado.localidade_slug, "porto-alegre")
        self.assertEqual(resultado.fonte, "viacep")

        # Verifica se foi salvo no banco
        consulta_salva = ConsultaCEP.objects.get(cep="91920-130")
        self.assertEqual(consulta_salva.localidade, "Porto Alegre")

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_cep_nao_encontrado(self, mock_get):
        """ViaCEP retornando erro deve tentar AwesomeAPI."""
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

        self.assertEqual(resultado.fonte, "awesomeapi")
        self.assertEqual(resultado.localidade, "Cidade")

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_consulta_viacep_erro_string_faz_fallback(self, mock_get):
        """ViaCEP retornando {"erro": "true"} (string) deve tentar AwesomeAPI."""
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

        self.assertEqual(resultado.fonte, "awesomeapi")
        self.assertEqual(resultado.localidade, "Uruguaiana")
        self.assertEqual(resultado.uf, "RS")
        self.assertEqual(resultado.cep, "97500-140")


class CEPServiceAwesomeAPITest(TestCase):
    """Testes de fallback para AwesomeAPI."""

    def setUp(self):
        self.service = CEPService()

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_fallback_awesomeapi_quando_viacep_falha(self, mock_get):
        """Quando ViaCEP falha, deve consultar AwesomeAPI."""
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

        self.assertEqual(resultado.fonte, "awesomeapi")
        self.assertEqual(resultado.localidade, "Porto Alegre")
        self.assertEqual(resultado.logradouro, "Rua Fallback")

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_cep_nao_encontrado_em_nenhum_provedor(self, mock_get):
        """CEP não encontrado em nenhum provedor deve lançar exceção."""
        mock_response_viacep = MagicMock()
        mock_response_viacep.json.return_value = {"erro": True}
        mock_response_viacep.raise_for_status = MagicMock()

        mock_response_awesome = MagicMock()
        mock_response_awesome.json.return_value = {"status": 404}
        mock_response_awesome.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_viacep, mock_response_awesome]

        with self.assertRaises(CEPNaoEncontradoError) as context:
            self.service.consultar("00000000")

        self.assertIn("00000-000", str(context.exception))

    @patch("bodepontoio.services.cep_service.requests.Session.get")
    def test_ambos_provedores_falham_com_excecao(self, mock_get):
        """Quando ambos provedores falham, deve lançar exceção."""
        import requests

        mock_get.side_effect = requests.RequestException("Erro de conexão")

        with self.assertRaises(CEPNaoEncontradoError):
            self.service.consultar("91920130")


class CEPServiceBuscarPorSlugTest(TestCase):
    """Testes de busca por slug."""

    def setUp(self):
        self.service = CEPService()
        ConsultaCEP.objects.create(
            cep="91920-130",
            logradouro="Rua A",
            bairro="Centro",
            localidade="Porto Alegre",
            uf="RS",
            localidade_slug="porto-alegre",
            fonte="viacep",
        )
        ConsultaCEP.objects.create(
            cep="91920-140",
            logradouro="Rua B",
            bairro="Bairro X",
            localidade="Porto Alegre",
            uf="RS",
            localidade_slug="porto-alegre",
            fonte="viacep",
        )
        ConsultaCEP.objects.create(
            cep="01001-000",
            logradouro="Praça da Sé",
            bairro="Sé",
            localidade="São Paulo",
            uf="SP",
            localidade_slug="sao-paulo",
            fonte="viacep",
        )

    def test_buscar_por_slug_retorna_multiplos(self):
        """Busca por slug deve retornar todos os CEPs da cidade."""
        resultado = self.service.buscar_por_slug("porto-alegre")

        self.assertEqual(len(resultado), 2)
        ceps = [r.cep for r in resultado]
        self.assertIn("91920-130", ceps)
        self.assertIn("91920-140", ceps)

    def test_buscar_por_slug_retorna_unico(self):
        """Busca por slug com um único CEP."""
        resultado = self.service.buscar_por_slug("sao-paulo")

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].localidade, "São Paulo")

    def test_buscar_por_slug_nao_encontrado(self):
        """Busca por slug inexistente retorna lista vazia."""
        resultado = self.service.buscar_por_slug("cidade-inexistente")

        self.assertEqual(len(resultado), 0)


class DadosCEPTest(TestCase):
    """Testes do dataclass DadosCEP."""

    def test_criacao_dados_cep(self):
        """DadosCEP deve ser criado corretamente."""
        dados = DadosCEP(
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

        self.assertEqual(dados.cep, "01001-000")
        self.assertEqual(dados.localidade, "São Paulo")
        self.assertEqual(dados.localidade_slug, "sao-paulo")


class ConsultaCEPModelTest(TestCase):
    """Testes do modelo ConsultaCEP."""

    def test_slug_gerado_automaticamente(self):
        """Slug deve ser gerado automaticamente ao salvar."""
        consulta = ConsultaCEP.objects.create(
            cep="12345-678",
            logradouro="Rua Teste",
            bairro="Centro",
            localidade="São José dos Campos",
            uf="SP",
            fonte="viacep",
        )

        self.assertEqual(consulta.localidade_slug, "sao-jose-dos-campos")

    def test_slug_nao_sobrescreve_existente(self):
        """Slug existente não deve ser sobrescrito."""
        consulta = ConsultaCEP.objects.create(
            cep="12345-678",
            logradouro="Rua Teste",
            bairro="Centro",
            localidade="São José dos Campos",
            uf="SP",
            localidade_slug="slug-customizado",
            fonte="viacep",
        )

        self.assertEqual(consulta.localidade_slug, "slug-customizado")

    def test_str_representation(self):
        """Representação string do modelo."""
        consulta = ConsultaCEP.objects.create(
            cep="01001-000",
            logradouro="Praça da Sé",
            bairro="Sé",
            localidade="São Paulo",
            uf="SP",
            fonte="viacep",
        )

        self.assertEqual(str(consulta), "01001-000 - São Paulo/SP")

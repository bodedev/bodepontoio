"""Serviço de consulta de CEP com fallback entre provedores."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests
from django.utils.text import slugify

from bodepontoio.models import ConsultaCEP

logger = logging.getLogger(__name__)


@dataclass
class DadosCEP:
    """Dados retornados de uma consulta de CEP."""

    cep: str
    logradouro: str
    complemento: str
    bairro: str
    localidade: str
    uf: str
    ibge: str
    ddd: str
    localidade_slug: str
    fonte: str


class CEPNaoEncontradoError(Exception):
    """Exceção para CEP não encontrado em nenhum provedor."""

    pass


class CEPInvalidoError(Exception):
    """Exceção para CEP com formato inválido."""

    pass


class CEPService:
    """
    Serviço de consulta de CEP com cache em banco de dados.

    Consulta primeiro o banco de dados local. Se não encontrar,
    tenta o ViaCEP e, em caso de falha, o AwesomeAPI.
    """

    VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
    AWESOMEAPI_URL = "https://cep.awesomeapi.com.br/json/{cep}"
    TIMEOUT = 10

    def __init__(self):
        self._session = requests.Session()

    @staticmethod
    def _limpar_cep(cep: str) -> str:
        """Remove caracteres não numéricos do CEP."""
        return re.sub(r"\D", "", cep)

    @staticmethod
    def _validar_cep(cep: str) -> None:
        """Valida o formato do CEP."""
        if not cep or len(cep) != 8 or not cep.isdigit():
            raise CEPInvalidoError(f"CEP inválido: {cep}. Deve conter 8 dígitos.")

    @staticmethod
    def _formatar_cep(cep: str) -> str:
        """Formata o CEP no padrão XXXXX-XXX."""
        return f"{cep[:5]}-{cep[5:]}"

    def _consultar_banco(self, cep: str) -> Optional[ConsultaCEP]:
        """Consulta o CEP no banco de dados local."""
        try:
            return ConsultaCEP.objects.get(cep=cep)
        except ConsultaCEP.DoesNotExist:
            return None

    def _consultar_viacep(self, cep: str) -> Optional[dict]:
        """Consulta o CEP no ViaCEP."""
        url = self.VIACEP_URL.format(cep=cep)
        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("erro"):
                logger.info("CEP %s não encontrado no ViaCEP", cep)
                return None

            return {
                "cep": data.get("cep", "").replace("-", ""),
                "logradouro": data.get("logradouro", ""),
                "complemento": data.get("complemento", ""),
                "bairro": data.get("bairro", ""),
                "localidade": data.get("localidade", ""),
                "uf": data.get("uf", ""),
                "ibge": data.get("ibge", ""),
                "ddd": data.get("ddd", ""),
                "fonte": "viacep",
            }
        except requests.RequestException as e:
            logger.warning("Erro ao consultar ViaCEP para %s: %s", cep, e)
            return None

    def _consultar_awesomeapi(self, cep: str) -> Optional[dict]:
        """Consulta o CEP no AwesomeAPI."""
        url = self.AWESOMEAPI_URL.format(cep=cep)
        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == 404 or "error" in data:
                logger.info("CEP %s não encontrado no AwesomeAPI", cep)
                return None

            return {
                "cep": data.get("cep", "").replace("-", ""),
                "logradouro": data.get("address", ""),
                "complemento": "",
                "bairro": data.get("district", ""),
                "localidade": data.get("city", ""),
                "uf": data.get("state", ""),
                "ibge": data.get("city_ibge", ""),
                "ddd": data.get("ddd", ""),
                "fonte": "awesomeapi",
            }
        except requests.RequestException as e:
            logger.warning("Erro ao consultar AwesomeAPI para %s: %s", cep, e)
            return None

    def _salvar_consulta(self, dados: dict) -> ConsultaCEP:
        """Salva a consulta no banco de dados."""
        cep_formatado = self._formatar_cep(dados["cep"])
        return ConsultaCEP.objects.create(
            cep=cep_formatado,
            logradouro=dados["logradouro"],
            complemento=dados["complemento"],
            bairro=dados["bairro"],
            localidade=dados["localidade"],
            uf=dados["uf"],
            ibge=dados["ibge"],
            ddd=dados["ddd"],
            localidade_slug=slugify(dados["localidade"]),
            fonte=dados["fonte"],
        )

    def _modelo_para_dados(self, consulta: ConsultaCEP) -> DadosCEP:
        """Converte um modelo ConsultaCEP para DadosCEP."""
        return DadosCEP(
            cep=consulta.cep,
            logradouro=consulta.logradouro,
            complemento=consulta.complemento,
            bairro=consulta.bairro,
            localidade=consulta.localidade,
            uf=consulta.uf,
            ibge=consulta.ibge,
            ddd=consulta.ddd,
            localidade_slug=consulta.localidade_slug,
            fonte=consulta.fonte,
        )

    def consultar(self, cep: str) -> DadosCEP:
        """
        Consulta um CEP.

        Primeiro verifica o cache local (banco de dados).
        Se não encontrar, consulta o ViaCEP.
        Se o ViaCEP falhar, consulta o AwesomeAPI.
        Salva o resultado no banco de dados para consultas futuras.

        Args:
            cep: O CEP a ser consultado (com ou sem formatação).

        Returns:
            DadosCEP com as informações do endereço.

        Raises:
            CEPInvalidoError: Se o CEP tiver formato inválido.
            CEPNaoEncontradoError: Se o CEP não for encontrado em nenhum provedor.
        """
        cep_limpo = self._limpar_cep(cep)
        self._validar_cep(cep_limpo)
        cep_formatado = self._formatar_cep(cep_limpo)

        # 1. Consulta no banco de dados
        consulta_cache = self._consultar_banco(cep_formatado)
        if consulta_cache:
            logger.debug("CEP %s encontrado no cache", cep_formatado)
            return self._modelo_para_dados(consulta_cache)

        # 2. Consulta no ViaCEP
        dados = self._consultar_viacep(cep_limpo)

        # 3. Fallback para AwesomeAPI
        if not dados:
            dados = self._consultar_awesomeapi(cep_limpo)

        # 4. Se não encontrou em nenhum provedor
        if not dados:
            raise CEPNaoEncontradoError(f"CEP {cep_formatado} não encontrado.")

        # 5. Salva no banco e retorna
        consulta = self._salvar_consulta(dados)
        logger.info("CEP %s salvo no cache (fonte: %s)", cep_formatado, dados["fonte"])
        return self._modelo_para_dados(consulta)

    def buscar_por_slug(self, localidade_slug: str) -> list[ConsultaCEP]:
        """
        Busca CEPs por slug da localidade.

        Args:
            localidade_slug: Slug da cidade para busca.

        Returns:
            Lista de ConsultaCEP correspondentes ao slug.
        """
        return list(ConsultaCEP.objects.filter(localidade_slug=localidade_slug))


# Instância singleton para uso conveniente
cep_service = CEPService()

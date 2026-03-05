import logging

import sentry_sdk

logger = logging.getLogger(__name__)


def count(key, value=1, unit="none", attributes=None):
    """Incrementa um contador de métrica.

    Args:
        key: Nome da métrica.
        value: Valor a incrementar (padrão: 1).
        unit: Unidade da métrica (padrão: "none").
        attributes: Dicionário de tags para filtrar a métrica.
    """
    try:
        sentry_sdk.metrics.count(key, value=value, unit=unit, attributes=attributes)
    except Exception:
        logger.exception("Erro ao registrar métrica count: %s", key)


def distribution(key, value, unit="none", attributes=None):
    """Registra um valor em uma distribuição de métrica.

    Args:
        key: Nome da métrica.
        value: Valor a registrar.
        unit: Unidade da métrica (padrão: "none").
        attributes: Dicionário de tags para filtrar a métrica.
    """
    try:
        sentry_sdk.metrics.distribution(key, value=value, unit=unit, attributes=attributes)
    except Exception:
        logger.exception("Erro ao registrar métrica distribution: %s", key)


def gauge(key, value, attributes=None):
    """Registra um valor gauge de métrica.

    Args:
        key: Nome da métrica.
        value: Valor a registrar.
        unit: Unidade da métrica (padrão: "none").
        attributes: Dicionário de tags para filtrar a métrica.
    """
    try:
        sentry_sdk.metrics.gauge(key, value=value, attributes=attributes)
    except Exception:
        logger.exception("Erro ao registrar métrica gauge: %s", key)

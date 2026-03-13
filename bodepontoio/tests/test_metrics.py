import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

# sentry_sdk pode não estar instalado no ambiente de teste,
# então criamos um mock do módulo antes de importar metrics.
_sentry_mock = MagicMock()
_needs_cleanup = 'sentry_sdk' not in sys.modules
if _needs_cleanup:
    sys.modules['sentry_sdk'] = _sentry_mock

from bodepontoio.metrics.metrics import count, distribution, gauge  # noqa: E402


class TestMetrics(SimpleTestCase):

    def setUp(self):
        _sentry_mock.reset_mock()

    def test_count(self):
        count('test.metric', value=5)
        _sentry_mock.metrics.count.assert_called_once_with(
            'test.metric', value=5, unit='none', attributes=None
        )

    def test_distribution(self):
        distribution('test.dist', 42, unit='ms')
        _sentry_mock.metrics.distribution.assert_called_once_with(
            'test.dist', value=42, unit='ms', attributes=None
        )

    def test_gauge(self):
        gauge('test.gauge', 100, attributes={'env': 'prod'})
        _sentry_mock.metrics.gauge.assert_called_once_with(
            'test.gauge', value=100, attributes={'env': 'prod'}
        )

    def test_count_handles_exception(self):
        _sentry_mock.metrics.count.side_effect = RuntimeError('fail')
        count('test.metric')
        _sentry_mock.metrics.count.side_effect = None

    def test_distribution_handles_exception(self):
        _sentry_mock.metrics.distribution.side_effect = RuntimeError('fail')
        distribution('test.dist', 1)
        _sentry_mock.metrics.distribution.side_effect = None

    def test_gauge_handles_exception(self):
        _sentry_mock.metrics.gauge.side_effect = RuntimeError('fail')
        gauge('test.gauge', 1)
        _sentry_mock.metrics.gauge.side_effect = None

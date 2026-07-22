from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver

from bodepontoio.utils.email.mx import domain_has_mx_record


class TestDomainHasMxRecord:
    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_domain_with_mx_record_returns_true(self, mock_resolver_cls):
        mock_resolver_cls.return_value.resolve.return_value = MagicMock()
        assert domain_has_mx_record("example.com") is True

    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_nxdomain_returns_false(self, mock_resolver_cls):
        mock_resolver_cls.return_value.resolve.side_effect = dns.resolver.NXDOMAIN()
        assert domain_has_mx_record("gamail.comm") is False

    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_noanswer_returns_false(self, mock_resolver_cls):
        mock_resolver_cls.return_value.resolve.side_effect = dns.resolver.NoAnswer()
        assert domain_has_mx_record("no-mx.com") is False

    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_timeout_returns_none(self, mock_resolver_cls):
        mock_resolver_cls.return_value.resolve.side_effect = dns.exception.Timeout()
        assert domain_has_mx_record("slow-domain.com") is None

    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_generic_dns_exception_returns_none(self, mock_resolver_cls):
        mock_resolver_cls.return_value.resolve.side_effect = dns.exception.DNSException("no nameservers")
        assert domain_has_mx_record("unreachable-resolver.com") is None

    @patch("bodepontoio.utils.email.mx.dns.resolver.Resolver")
    def test_timeout_is_configured_on_resolver(self, mock_resolver_cls):
        domain_has_mx_record("example.com", timeout=5.0)
        resolver_instance = mock_resolver_cls.return_value
        assert resolver_instance.timeout == 5.0
        assert resolver_instance.lifetime == 5.0

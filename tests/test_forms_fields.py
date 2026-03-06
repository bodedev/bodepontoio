from unittest.mock import MagicMock, patch

import dns.exception
from django.forms import ValidationError
import pytest

from bodepontoio.utils.forms.fields import ValidatingEmailField


class TestValidatingEmailField:
    def setup_method(self):
        self.field = ValidatingEmailField()

    @patch("bodepontoio.utils.forms.fields.dns.resolver.resolve")
    def test_valid_email_with_mx_record(self, mock_resolve):
        mock_resolve.return_value = MagicMock()
        result = self.field.clean("user@example.com")
        assert result == "user@example.com"
        mock_resolve.assert_called_once_with("example.com", "MX")

    @patch("bodepontoio.utils.forms.fields.dns.resolver.resolve")
    def test_invalid_domain_raises_validation_error(self, mock_resolve):
        mock_resolve.side_effect = dns.exception.DNSException("Domain not found")
        with pytest.raises(ValidationError) as exc_info:
            self.field.clean("user@invalid-domain-xyz.com")
        assert str(exc_info.value.messages[0]) == "Este e-mail não é válido!"

    @patch("bodepontoio.utils.forms.fields.dns.resolver.resolve")
    def test_dns_timeout_raises_validation_error(self, mock_resolve):
        mock_resolve.side_effect = dns.exception.Timeout()
        with pytest.raises(ValidationError):
            self.field.clean("user@slow-domain.com")

    @patch("bodepontoio.utils.forms.fields.dns.resolver.resolve")
    def test_dns_nxdomain_raises_validation_error(self, mock_resolve):
        mock_resolve.side_effect = dns.exception.DNSException()
        with pytest.raises(ValidationError):
            self.field.clean("user@nonexistent.com")

    def test_invalid_email_format_raises_validation_error(self):
        with pytest.raises(ValidationError):
            self.field.clean("invalid-email")

    def test_empty_email_when_not_required(self):
        field = ValidatingEmailField(required=False)
        result = field.clean("")
        assert result == ""

    def test_empty_email_when_required(self):
        with pytest.raises(ValidationError):
            self.field.clean("")

    @patch("bodepontoio.utils.forms.fields.dns.resolver.resolve")
    def test_accepts_uppercase_email(self, mock_resolve):
        mock_resolve.return_value = MagicMock()
        result = self.field.clean("USER@EXAMPLE.COM")
        assert result == "USER@EXAMPLE.COM"

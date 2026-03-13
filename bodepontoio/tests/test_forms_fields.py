from unittest.mock import MagicMock, patch

import dns.exception
from django.forms import ValidationError
from django.test import SimpleTestCase

from bodepontoio.utils.forms.fields import ValidatingEmailField


class TestValidatingEmailField(SimpleTestCase):

    def setUp(self):
        self.field = ValidatingEmailField()

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_valid_email_with_mx_record(self, mock_query):
        mock_query.return_value = MagicMock()
        result = self.field.clean("user@example.com")
        self.assertEqual(result, "user@example.com")
        mock_query.assert_called_once_with("example.com", "MX")

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_noanswer_raises_validation_error(self, mock_resolve):
        mock_resolve.side_effect = dns.resolver.NoAnswer()
        with self.assertRaises(ValidationError):
            self.field.clean("user@no-answer.com")

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_invalid_domain_raises_validation_error(self, mock_query):
        mock_query.side_effect = dns.exception.DNSException("Domain not found")
        with self.assertRaises(ValidationError) as context:
            self.field.clean("user@invalid-domain-xyz.com")
        self.assertEqual(str(context.exception.messages[0]), "Este e-mail não é válido!")

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_dns_timeout_raises_validation_error(self, mock_query):
        mock_query.side_effect = dns.exception.Timeout()
        with self.assertRaises(ValidationError):
            self.field.clean("user@slow-domain.com")

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_dns_nxdomain_raises_validation_error(self, mock_query):
        mock_query.side_effect = dns.exception.DNSException()
        with self.assertRaises(ValidationError):
            self.field.clean("user@nonexistent.com")

    def test_invalid_email_format_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.field.clean("invalid-email")

    def test_empty_email_when_not_required(self):
        field = ValidatingEmailField(required=False)
        result = field.clean("")
        self.assertEqual(result, "")

    def test_empty_email_when_required(self):
        with self.assertRaises(ValidationError):
            self.field.clean("")

    @patch('bodepontoio.utils.forms.fields.dns.resolver.resolve')
    def test_accepts_uppercase_email(self, mock_query):
        mock_query.return_value = MagicMock()
        result = self.field.clean("USER@EXAMPLE.COM")
        self.assertEqual(result, "USER@EXAMPLE.COM")

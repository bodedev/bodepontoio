from django.test import SimpleTestCase

from bodepontoio.utils.email.ofuscate import obfuscate_email


class TestObfuscateEmail(SimpleTestCase):

    def test_obfuscates_standard_email(self):
        result = obfuscate_email("ironworld@gmail.com")
        self.assertEqual(result, "ir*******@g****.com")

    def test_obfuscates_with_custom_local_keep(self):
        result = obfuscate_email("ironworld@gmail.com", local_keep=4)
        self.assertEqual(result, "iron*****@g****.com")

    def test_obfuscates_with_custom_domain_keep(self):
        result = obfuscate_email("ironworld@gmail.com", domain_keep=3)
        self.assertEqual(result, "ir*******@gma**.com")

    def test_obfuscates_with_custom_mask_char(self):
        result = obfuscate_email("ironworld@gmail.com", mask_char="#")
        self.assertEqual(result, "ir#######@g####.com")

    def test_short_local_part_not_masked(self):
        result = obfuscate_email("ab@gmail.com", local_keep=2)
        self.assertEqual(result, "ab@g****.com")

    def test_short_domain_name_not_masked(self):
        result = obfuscate_email("user@a.com", domain_keep=1)
        self.assertEqual(result, "us**@a.com")

    def test_email_with_subdomain(self):
        result = obfuscate_email("user@mail.example.com")
        self.assertEqual(result, "us**@m***.example.com")

    def test_email_with_country_tld(self):
        result = obfuscate_email("teste@empresa.com.br")
        self.assertEqual(result, "te***@e******.com.br")

    def test_invalid_email_returns_unchanged(self):
        result = obfuscate_email("invalid-email")
        self.assertEqual(result, "invalid-email")

    def test_email_without_at_returns_unchanged(self):
        result = obfuscate_email("no_at_symbol")
        self.assertEqual(result, "no_at_symbol")

    def test_email_with_multiple_at_returns_unchanged(self):
        result = obfuscate_email("user@@domain.com")
        self.assertEqual(result, "user@@domain.com")

    def test_domain_without_dot(self):
        result = obfuscate_email("user@localhost")
        self.assertEqual(result, "us**@l********")

    def test_single_char_local_part(self):
        result = obfuscate_email("a@gmail.com", local_keep=2)
        self.assertEqual(result, "a@g****.com")

    def test_empty_string_returns_unchanged(self):
        result = obfuscate_email("")
        self.assertEqual(result, "")

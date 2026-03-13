from bodepontoio.utils.email.ofuscate import obfuscate_email


class TestObfuscateEmail:
    def test_obfuscates_standard_email(self):
        assert obfuscate_email("ironworld@gmail.com") == "ir*******@g****.com"

    def test_obfuscates_with_custom_local_keep(self):
        assert obfuscate_email("ironworld@gmail.com", local_keep=4) == "iron*****@g****.com"

    def test_obfuscates_with_custom_domain_keep(self):
        assert obfuscate_email("ironworld@gmail.com", domain_keep=3) == "ir*******@gma**.com"

    def test_obfuscates_with_custom_mask_char(self):
        assert obfuscate_email("ironworld@gmail.com", mask_char="#") == "ir#######@g####.com"

    def test_short_local_part_not_masked(self):
        assert obfuscate_email("ab@gmail.com", local_keep=2) == "ab@g****.com"

    def test_short_domain_name_not_masked(self):
        assert obfuscate_email("user@a.com", domain_keep=1) == "us**@a.com"

    def test_email_with_subdomain(self):
        assert obfuscate_email("user@mail.example.com") == "us**@m***.example.com"

    def test_email_with_country_tld(self):
        assert obfuscate_email("teste@empresa.com.br") == "te***@e******.com.br"

    def test_invalid_email_returns_unchanged(self):
        assert obfuscate_email("invalid-email") == "invalid-email"

    def test_email_without_at_returns_unchanged(self):
        assert obfuscate_email("no_at_symbol") == "no_at_symbol"

    def test_email_with_multiple_at_returns_unchanged(self):
        assert obfuscate_email("user@@domain.com") == "user@@domain.com"

    def test_domain_without_dot(self):
        assert obfuscate_email("user@localhost") == "us**@l********"

    def test_single_char_local_part(self):
        assert obfuscate_email("a@gmail.com", local_keep=2) == "a@g****.com"

    def test_empty_string_returns_unchanged(self):
        assert obfuscate_email("") == ""

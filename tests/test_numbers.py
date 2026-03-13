from bodepontoio.utils.numbers import grana


class TestGrana:
    def test_formats_integer_value(self):
        assert grana(1000) == "1.000,00"

    def test_formats_float_value(self):
        assert grana(1234.56) == "1.234,56"

    def test_formats_value_with_prefix(self):
        assert grana(1000, prefixo="R$") == "R$ 1.000,00"

    def test_formats_zero(self):
        assert grana(0) == "0,00"

    def test_handles_none(self):
        assert grana(None) == "0,00"

    def test_handles_empty_string(self):
        assert grana("") == "0,00"

    def test_formats_negative_value(self):
        assert grana(-1500.75) == "-1.500,75"

    def test_formats_negative_value_with_prefix(self):
        assert grana(-500, prefixo="R$") == "R$ -500,00"

    def test_formats_large_number(self):
        assert grana(1234567890.12) == "1.234.567.890,12"

    def test_formats_small_decimal(self):
        assert grana(0.5) == "0,50"

    def test_formats_single_digit_decimal(self):
        assert grana(45.5) == "45,50"

    def test_truncates_extra_decimal_places(self):
        assert grana(100.999) == "100,99"

    def test_formats_value_without_decimal_part(self):
        assert grana(500) == "500,00"

    def test_formats_hundreds(self):
        assert grana(999) == "999,00"

    def test_formats_thousands(self):
        assert grana(9999) == "9.999,00"

    def test_formats_with_dollar_prefix(self):
        assert grana(250.50, prefixo="$") == "$ 250,50"

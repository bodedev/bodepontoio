from django.test import SimpleTestCase

from bodepontoio.utils.numbers import grana


class TestGrana(SimpleTestCase):

    def test_formats_integer_value(self):
        result = grana(1000)
        self.assertEqual(result, "1.000,00")

    def test_formats_float_value(self):
        result = grana(1234.56)
        self.assertEqual(result, "1.234,56")

    def test_formats_value_with_prefix(self):
        result = grana(1000, prefixo="R$")
        self.assertEqual(result, "R$ 1.000,00")

    def test_formats_zero(self):
        result = grana(0)
        self.assertEqual(result, "0,00")

    def test_handles_none(self):
        result = grana(None)
        self.assertEqual(result, "0,00")

    def test_handles_empty_string(self):
        result = grana("")
        self.assertEqual(result, "0,00")

    def test_formats_negative_value(self):
        result = grana(-1500.75)
        self.assertEqual(result, "-1.500,75")

    def test_formats_negative_value_with_prefix(self):
        result = grana(-500, prefixo="R$")
        self.assertEqual(result, "R$ -500,00")

    def test_formats_large_number(self):
        result = grana(1234567890.12)
        self.assertEqual(result, "1.234.567.890,12")

    def test_formats_small_decimal(self):
        result = grana(0.5)
        self.assertEqual(result, "0,50")

    def test_formats_single_digit_decimal(self):
        result = grana(45.5)
        self.assertEqual(result, "45,50")

    def test_truncates_extra_decimal_places(self):
        result = grana(100.999)
        self.assertEqual(result, "100,99")

    def test_formats_value_without_decimal_part(self):
        result = grana(500)
        self.assertEqual(result, "500,00")

    def test_formats_hundreds(self):
        result = grana(999)
        self.assertEqual(result, "999,00")

    def test_formats_thousands(self):
        result = grana(9999)
        self.assertEqual(result, "9.999,00")

    def test_formats_with_dollar_prefix(self):
        result = grana(250.50, prefixo="$")
        self.assertEqual(result, "$ 250,50")

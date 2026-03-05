from django.test import SimpleTestCase

from bodepontoio.utils.dates import month_to_string


class TestMonthToString(SimpleTestCase):

    def test_january(self):
        self.assertEqual(month_to_string(1), "Janeiro")

    def test_february(self):
        self.assertEqual(month_to_string(2), "Fevereiro")

    def test_march(self):
        self.assertEqual(month_to_string(3), "Março")

    def test_april(self):
        self.assertEqual(month_to_string(4), "Abril")

    def test_may(self):
        self.assertEqual(month_to_string(5), "Maio")

    def test_june(self):
        self.assertEqual(month_to_string(6), "Junho")

    def test_july(self):
        self.assertEqual(month_to_string(7), "Julho")

    def test_august(self):
        self.assertEqual(month_to_string(8), "Agosto")

    def test_september(self):
        self.assertEqual(month_to_string(9), "Setembro")

    def test_october(self):
        self.assertEqual(month_to_string(10), "Outubro")

    def test_november(self):
        self.assertEqual(month_to_string(11), "Novembro")

    def test_december(self):
        self.assertEqual(month_to_string(12), "Dezembro")

    def test_invalid_month_zero(self):
        with self.assertRaises(ValueError) as context:
            month_to_string(0)
        self.assertEqual(str(context.exception), "Mês inválido!")

    def test_invalid_month_negative(self):
        with self.assertRaises(ValueError) as context:
            month_to_string(-1)
        self.assertEqual(str(context.exception), "Mês inválido!")

    def test_invalid_month_greater_than_twelve(self):
        with self.assertRaises(ValueError) as context:
            month_to_string(13)
        self.assertEqual(str(context.exception), "Mês inválido!")

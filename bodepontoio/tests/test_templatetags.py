from decimal import Decimal

from django.test import RequestFactory, SimpleTestCase

from bodepontoio.templatetags.bodepontoio_tags import (
    grana_filter,
    multiply,
    roi,
    url_replace,
)


class TestGranaFilter(SimpleTestCase):

    def test_formats_value(self):
        self.assertEqual(grana_filter(1000), "1.000,00")

    def test_formats_with_prefix(self):
        self.assertEqual(grana_filter(1000, prefixo="R$"), "R$ 1.000,00")

    def test_handles_none(self):
        self.assertEqual(grana_filter(None), "0,00")


class TestUrlReplace(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_replaces_query_param(self):
        request = self.factory.get('/?page=1&q=test')
        result = url_replace(request, 'page', '2')
        self.assertIn('page=2', result)
        self.assertIn('q=test', result)

    def test_adds_new_query_param(self):
        request = self.factory.get('/')
        result = url_replace(request, 'page', '1')
        self.assertIn('page=1', result)


class TestMultiply(SimpleTestCase):

    def test_multiplies_integers(self):
        self.assertEqual(multiply(5, 3), 15)

    def test_multiplies_floats(self):
        self.assertAlmostEqual(multiply(2.5, 4), 10.0)


class TestRoi(SimpleTestCase):

    def test_calculates_roi(self):
        result = roi(Decimal('150'), Decimal('100'))
        self.assertEqual(result, Decimal('50'))

    def test_negative_roi(self):
        result = roi(Decimal('80'), Decimal('100'))
        self.assertEqual(result, Decimal('-20'))

from django.test import SimpleTestCase

from bodepontoio.utils.database.mysql import Round


class TestRound(SimpleTestCase):

    def test_round_function_name(self):
        self.assertEqual(Round.function, 'ROUND')

    def test_round_template(self):
        self.assertEqual(Round.template, '%(function)s(%(expressions)s, 2)')

    def test_round_is_func_subclass(self):
        from django.db.models import Func
        self.assertTrue(issubclass(Round, Func))

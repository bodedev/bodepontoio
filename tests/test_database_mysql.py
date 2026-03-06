from django.db.models import Func

from bodepontoio.utils.database.mysql import Round


class TestRound:
    def test_round_function_name(self):
        assert Round.function == "ROUND"

    def test_round_template(self):
        assert Round.template == "%(function)s(%(expressions)s, 2)"

    def test_round_is_func_subclass(self):
        assert issubclass(Round, Func)

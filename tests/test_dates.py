import pytest

from bodepontoio.utils.dates import month_to_string


class TestMonthToString:
    def test_january(self):
        assert month_to_string(1) == "Janeiro"

    def test_february(self):
        assert month_to_string(2) == "Fevereiro"

    def test_march(self):
        assert month_to_string(3) == "Março"

    def test_april(self):
        assert month_to_string(4) == "Abril"

    def test_may(self):
        assert month_to_string(5) == "Maio"

    def test_june(self):
        assert month_to_string(6) == "Junho"

    def test_july(self):
        assert month_to_string(7) == "Julho"

    def test_august(self):
        assert month_to_string(8) == "Agosto"

    def test_september(self):
        assert month_to_string(9) == "Setembro"

    def test_october(self):
        assert month_to_string(10) == "Outubro"

    def test_november(self):
        assert month_to_string(11) == "Novembro"

    def test_december(self):
        assert month_to_string(12) == "Dezembro"

    def test_invalid_month_zero(self):
        with pytest.raises(ValueError, match="Mês inválido!"):
            month_to_string(0)

    def test_invalid_month_negative(self):
        with pytest.raises(ValueError, match="Mês inválido!"):
            month_to_string(-1)

    def test_invalid_month_greater_than_twelve(self):
        with pytest.raises(ValueError, match="Mês inválido!"):
            month_to_string(13)

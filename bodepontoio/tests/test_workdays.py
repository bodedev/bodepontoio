from datetime import datetime

from django.test import SimpleTestCase

from bodepontoio.utils.workdays import num_workdays, workday


class TestWorkday(SimpleTestCase):

    def test_adds_workdays_skipping_weekend(self):
        # Sexta-feira, 13 de dezembro de 2024
        start = datetime(2024, 12, 13)
        result = workday(start, 1)
        # Deve retornar segunda-feira, 16 de dezembro
        self.assertEqual(result.day, 16)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2024)

    def test_adds_two_workdays(self):
        # Terça-feira, 24 de dezembro de 2024
        start = datetime(2024, 12, 24)
        result = workday(start, 2)
        # Pula 25/12 (Natal), dia 1 = 26/12, dia 2 = 27/12 (sexta)
        self.assertEqual(result.day, 27)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2024)

    def test_adds_zero_workdays(self):
        start = datetime(2024, 12, 10)
        result = workday(start, 0)
        self.assertEqual(result.day, 10)
        self.assertEqual(result.month, 12)

    def test_adds_workdays_skipping_holiday(self):
        # 30 de dezembro de 2024 (segunda-feira)
        start = datetime(2024, 12, 30)
        result = workday(start, 3)
        # 30 + 3 dias úteis: 31 (1º), 01/01 pula (feriado), 02 (2º), 03 (3º)
        self.assertEqual(result.day, 3)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.year, 2025)

    def test_adds_five_workdays(self):
        # Segunda-feira, 9 de dezembro de 2024
        start = datetime(2024, 12, 9)
        result = workday(start, 5)
        # Segunda a sexta = 5 dias úteis
        self.assertEqual(result.day, 16)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2024)

    def test_workday_with_custom_empty_holidays(self):
        # 31 de dezembro de 2024 (terça-feira)
        start = datetime(2024, 12, 31)
        result = workday(start, 1, holidays=[])
        # Sem feriados, próximo dia útil é 01/01
        self.assertEqual(result.day, 1)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.year, 2025)

    def test_workday_start_on_saturday_with_many_days(self):
        # 28 de fevereiro de 2026 é sábado - caso que causava loop infinito
        start = datetime(2026, 2, 28, 10, 26, 53, 491215)
        result = workday(start, 80)
        # Deve ajustar para segunda 02/03 e calcular 80 dias úteis
        self.assertEqual(result.weekday() < 5, True)  # resultado deve ser dia útil
        self.assertEqual(result.date(), datetime(2026, 6, 26).date())

    def test_workday_start_on_sunday(self):
        # 01 de março de 2026 é domingo
        start = datetime(2026, 3, 1)
        result = workday(start, 1)
        # Deve ajustar para segunda 02/03 e somar 1 dia útil = terça 03/03
        self.assertEqual(result.date(), datetime(2026, 3, 3).date())

    def test_workday_start_on_saturday_zero_days(self):
        # Sábado com 0 dias deve avançar para segunda
        start = datetime(2026, 2, 28)
        result = workday(start, 0)
        # Ajusta para segunda 02/03
        self.assertEqual(result.date(), datetime(2026, 3, 2).date())

    def test_workday_start_on_saturday_one_day(self):
        # Sábado com 1 dia útil
        start = datetime(2026, 2, 28)
        result = workday(start, 1)
        # Ajusta para segunda 02/03 e soma 1 = terça 03/03
        self.assertEqual(result.date(), datetime(2026, 3, 3).date())

    def test_workday_large_days_with_holidays_in_range(self):
        # Segunda-feira 02/03/2026 com 80 dias úteis
        # Feriados no intervalo: 03/04, 21/04, 01/05, 04/06
        start = datetime(2026, 3, 2)
        result = workday(start, 80)
        self.assertEqual(result.weekday() < 5, True)
        self.assertEqual(result.date(), datetime(2026, 6, 26).date())

    def test_workday_negative_days_from_weekend(self):
        # Domingo com dias negativos deve recuar para sexta
        start = datetime(2026, 3, 1)  # Domingo
        result = workday(start, -1)
        # Ajusta para sexta 27/02 e recua 1 = quinta 26/02
        self.assertEqual(result.date(), datetime(2026, 2, 26).date())


class TestNumWorkdays(SimpleTestCase):

    def test_same_day_returns_zero(self):
        # A função retorna 0 quando início e fim são o mesmo dia
        start = datetime(2024, 12, 10)
        end = datetime(2024, 12, 10)
        result = num_workdays(start, end)
        self.assertEqual(result, 0)

    def test_counts_workdays_in_week(self):
        # Segunda a sexta (mesma semana) - não inclui o dia final
        start = datetime(2024, 12, 9)  # Segunda
        end = datetime(2024, 12, 13)  # Sexta
        result = num_workdays(start, end)
        # 9, 10, 11, 12 = 4 dias úteis (não inclui 13)
        self.assertEqual(result, 4)

    def test_excludes_weekends(self):
        # Segunda a próxima segunda (inclui um final de semana)
        start = datetime(2024, 12, 9)  # Segunda
        end = datetime(2024, 12, 16)  # Próxima segunda
        result = num_workdays(start, end)
        # 9, 10, 11, 12, 13 = 5 dias úteis (não inclui 16)
        self.assertEqual(result, 5)

    def test_excludes_holidays(self):
        # 23 a 26 de dezembro (inclui Natal)
        start = datetime(2024, 12, 23)  # Segunda
        end = datetime(2024, 12, 26)  # Quinta
        result = num_workdays(start, end)
        # 23, 24 (25 é feriado) = 2 dias úteis (não inclui 26)
        self.assertEqual(result, 2)

    def test_counts_workdays_with_custom_empty_holidays(self):
        start = datetime(2024, 12, 23)  # Segunda
        end = datetime(2024, 12, 26)  # Quinta
        result = num_workdays(start, end, holidays=[])
        # 23, 24, 25 = 3 dias úteis (não inclui 26, sem feriados)
        self.assertEqual(result, 3)

    def test_weekend_only_returns_zero(self):
        # Sábado e domingo apenas
        start = datetime(2024, 12, 14)  # Sábado
        end = datetime(2024, 12, 15)  # Domingo
        result = num_workdays(start, end, holidays=[])
        self.assertEqual(result, 0)

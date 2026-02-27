from datetime import datetime

from bodepontoio.utils.workdays import num_workdays, workday


class TestWorkday:
    def test_adds_workdays_skipping_weekend(self):
        start = datetime(2024, 12, 13)
        result = workday(start, 1)
        assert result.day == 16
        assert result.month == 12
        assert result.year == 2024

    def test_adds_two_workdays(self):
        start = datetime(2024, 12, 24)
        result = workday(start, 2)
        assert result.day == 27
        assert result.month == 12
        assert result.year == 2024

    def test_adds_zero_workdays(self):
        start = datetime(2024, 12, 10)
        result = workday(start, 0)
        assert result.day == 10
        assert result.month == 12

    def test_adds_workdays_skipping_holiday(self):
        start = datetime(2024, 12, 30)
        result = workday(start, 3)
        assert result.day == 3
        assert result.month == 1
        assert result.year == 2025

    def test_adds_five_workdays(self):
        start = datetime(2024, 12, 9)
        result = workday(start, 5)
        assert result.day == 16
        assert result.month == 12
        assert result.year == 2024

    def test_workday_with_custom_empty_holidays(self):
        start = datetime(2024, 12, 31)
        result = workday(start, 1, holidays=[])
        assert result.day == 1
        assert result.month == 1
        assert result.year == 2025

    def test_workday_start_on_saturday_with_many_days(self):
        start = datetime(2026, 2, 28, 10, 26, 53, 491215)
        result = workday(start, 80)
        assert result.weekday() < 5
        assert result.date() == datetime(2026, 6, 26).date()

    def test_workday_start_on_sunday(self):
        start = datetime(2026, 3, 1)
        result = workday(start, 1)
        assert result.date() == datetime(2026, 3, 3).date()

    def test_workday_start_on_saturday_zero_days(self):
        start = datetime(2026, 2, 28)
        result = workday(start, 0)
        assert result.date() == datetime(2026, 3, 2).date()

    def test_workday_start_on_saturday_one_day(self):
        start = datetime(2026, 2, 28)
        result = workday(start, 1)
        assert result.date() == datetime(2026, 3, 3).date()

    def test_workday_large_days_with_holidays_in_range(self):
        start = datetime(2026, 3, 2)
        result = workday(start, 80)
        assert result.weekday() < 5
        assert result.date() == datetime(2026, 6, 26).date()

    def test_workday_negative_days_from_weekend(self):
        start = datetime(2026, 3, 1)
        result = workday(start, -1)
        assert result.date() == datetime(2026, 2, 26).date()


class TestNumWorkdays:
    def test_same_day_returns_zero(self):
        start = datetime(2024, 12, 10)
        end = datetime(2024, 12, 10)
        assert num_workdays(start, end) == 0

    def test_counts_workdays_in_week(self):
        start = datetime(2024, 12, 9)
        end = datetime(2024, 12, 13)
        assert num_workdays(start, end) == 4

    def test_excludes_weekends(self):
        start = datetime(2024, 12, 9)
        end = datetime(2024, 12, 16)
        assert num_workdays(start, end) == 5

    def test_excludes_holidays(self):
        start = datetime(2024, 12, 23)
        end = datetime(2024, 12, 26)
        assert num_workdays(start, end) == 2

    def test_counts_workdays_with_custom_empty_holidays(self):
        start = datetime(2024, 12, 23)
        end = datetime(2024, 12, 26)
        assert num_workdays(start, end, holidays=[]) == 3

    def test_weekend_only_returns_zero(self):
        start = datetime(2024, 12, 14)
        end = datetime(2024, 12, 15)
        assert num_workdays(start, end, holidays=[]) == 0

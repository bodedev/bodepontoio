from datetime import datetime, timedelta

# started from the code of Casey Webster at
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/ddd39a02644540b7

# Define the weekday mnemonics to match the date.weekday function
(MON, TUE, WED, THU, FRI, SAT, SUN) = list(range(7))
weekends = (SAT, SUN)

HOLIDAYS = []

BRAZIL_HOLIDAYS_2023 = [
    datetime(2023, 10, 12),
    datetime(2023, 11, 2),
    datetime(2023, 11, 15),
    datetime(2023, 12, 25),
]

BRAZIL_HOLIDAYS_2024 = [
    datetime(2024, 1, 1),
    datetime(2024, 2, 10),
    datetime(2024, 2, 11),
    datetime(2024, 2, 12),
    datetime(2024, 2, 13),
    datetime(2024, 3, 29),
    datetime(2024, 4, 21),
    datetime(2024, 5, 1),
    datetime(2024, 6, 13),
    datetime(2024, 9, 7),
    datetime(2024, 9, 20),
    datetime(2024, 10, 12),
    datetime(2024, 11, 2),
    datetime(2024, 11, 15),
    datetime(2024, 12, 25),
]

BRAZIL_HOLIDAYS_2025 = [
    datetime(2025, 1, 1),  # Confraternização Universal
    datetime(2025, 3, 2),  # Carnaval (segunda-feira)
    datetime(2025, 3, 3),  # Carnaval (terça-feira)
    datetime(2025, 3, 4),  # Carnaval (ponto facultativo, quarta-feira de cinzas até meio-dia)
    datetime(2025, 4, 18),  # Sexta-feira Santa
    datetime(2025, 4, 21),  # Tiradentes
    datetime(2025, 5, 1),  # Dia do Trabalho
    datetime(2025, 6, 19),  # Corpus Christi (ponto facultativo, mas amplamente considerado)
    datetime(2025, 9, 7),  # Independência do Brasil
    datetime(2025, 10, 12),  # Nossa Senhora Aparecida
    datetime(2025, 11, 2),  # Finados
    datetime(2025, 11, 15),  # Proclamação da República
    datetime(2025, 11, 20),  # Dia da Conciência Negra
    datetime(2025, 12, 25),  # Natal
]

BRAZIL_HOLIDAYS_2026 = [
    datetime(2026, 1, 1),  # Confraternização Universal
    datetime(2026, 2, 16),  # Carnaval (Segunda-feira)
    datetime(2026, 2, 17),  # Carnaval (Terça-feira)
    datetime(2026, 2, 18),  # Quarta-feira de Cinzas (ponto facultativo até meio-dia)
    datetime(2026, 4, 3),  # Sexta-feira Santa
    datetime(2026, 4, 21),  # Tiradentes
    datetime(2026, 5, 1),  # Dia do Trabalho
    datetime(2026, 6, 4),  # Corpus Christi
    datetime(2026, 9, 7),  # Independência do Brasil
    datetime(2026, 10, 12),  # Nossa Senhora Aparecida
    datetime(2026, 11, 2),  # Finados
    datetime(2026, 11, 15),  # Proclamação da República
    datetime(2026, 11, 20),  # Dia da Consciência Negra
    datetime(2026, 12, 25),  # Natal
]

BRAZIL_HOLIDAYS_2027 = [
    datetime(2027, 1, 1),  # Confraternização Universal
    datetime(2027, 2, 8),  # Carnaval (Segunda-feira)
    datetime(2027, 2, 9),  # Carnaval (Terça-feira)
    datetime(2027, 3, 26),  # Sexta-feira Santa
    datetime(2027, 4, 21),  # Tiradentes
    datetime(2027, 5, 1),  # Dia do Trabalho
    datetime(2027, 5, 27),  # Corpus Christi
    datetime(2027, 9, 7),  # Independência do Brasil
    datetime(2027, 10, 12),  # Nossa Senhora Aparecida
    datetime(2027, 11, 2),  # Finados
    datetime(2027, 11, 15),  # Proclamação da República
    datetime(2027, 11, 20),  # Dia da Consciência Negra
    datetime(2027, 12, 25),  # Natal
]

BRAZIL_HOLIDAYS_2028 = [
    datetime(2028, 1, 1),  # Confraternização Universal
    datetime(2028, 2, 28),  # Carnaval (Segunda-feira)
    datetime(2028, 2, 29),  # Carnaval (Terça-feira)
    datetime(2028, 3, 1),  # Quarta-feira de Cinzas (ponto facultativo até meio-dia)
    datetime(2028, 4, 14),  # Sexta-feira Santa
    datetime(2028, 4, 21),  # Tiradentes
    datetime(2028, 5, 1),  # Dia do Trabalho
    datetime(2028, 6, 15),  # Corpus Christi
    datetime(2028, 9, 7),  # Independência do Brasil
    datetime(2028, 10, 12),  # Nossa Senhora Aparecida
    datetime(2028, 11, 2),  # Finados
    datetime(2028, 11, 15),  # Proclamação da República
    datetime(2028, 11, 20),  # Dia da Consciência Negra
    datetime(2028, 12, 25),  # Natal
]

HOLIDAYS.extend(BRAZIL_HOLIDAYS_2023)
HOLIDAYS.extend(BRAZIL_HOLIDAYS_2024)
HOLIDAYS.extend(BRAZIL_HOLIDAYS_2025)
HOLIDAYS.extend(BRAZIL_HOLIDAYS_2026)
HOLIDAYS.extend(BRAZIL_HOLIDAYS_2027)
HOLIDAYS.extend(BRAZIL_HOLIDAYS_2028)


def num_workdays(start_date, end_date, holidays=HOLIDAYS):
    delta_days = (end_date.date() - start_date.date()).days
    full_weeks, extra_days = divmod(delta_days, 7)
    # num_workdays = how many days/week you work * total # of weeks
    num_workdays = (full_weeks + 1) * (7 - len(weekends))
    # subtract out any working days that fall in the 'shortened week'
    for d in range(1, 8 - extra_days):
        if (end_date + timedelta(d)).weekday() not in weekends:
            num_workdays -= 1
    # skip holidays that fall on weekends
    holidays = [x for x in holidays if x.weekday() not in weekends]
    # subtract out any holidays
    for d in holidays:
        if d >= start_date and d <= end_date:
            num_workdays -= 1
    return num_workdays


def _in_between(a, b, x):
    return a <= x and x <= b or b <= x and x <= a


def workday(start_date, days, holidays=HOLIDAYS):
    if start_date.weekday() in weekends:
        if days >= 0:
            while start_date.weekday() in weekends:
                start_date += timedelta(days=1)
        else:
            while start_date.weekday() in weekends:
                start_date -= timedelta(days=1)
    full_weeks, extra_days = divmod(days, 7 - len(weekends))
    new_date = start_date + timedelta(weeks=full_weeks)
    for i in range(extra_days):
        new_date += timedelta(days=1)
        while new_date.weekday() in weekends:
            new_date += timedelta(days=1)
    delta = timedelta(days=1) if days >= 0 else timedelta(days=-1)
    # skip holidays that fall on weekends
    holidays = [x for x in holidays if x.weekday() not in weekends]
    holidays = [x for x in holidays if x != start_date]
    for d in sorted(holidays, reverse=(days < 0)):
        # if d in between start and current push it out one working day
        if _in_between(start_date, new_date, d):
            new_date += delta
            while new_date.weekday() in weekends:
                new_date += delta
    return new_date

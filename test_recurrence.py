import unittest
from datetime import date, datetime

from recurrence import RecurrenceRule, Pattern, EndType, get_occurrences


class TestOneOff(unittest.TestCase):
    def test_in_window(self):
        rule = RecurrenceRule(date(2026, 3, 10), Pattern.ONE_OFF, EndType.NEVER)
        self.assertEqual(
            get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31)),
            [date(2026, 3, 10)],
        )

    def test_outside_window(self):
        rule = RecurrenceRule(date(2026, 3, 10), Pattern.ONE_OFF, EndType.NEVER)
        self.assertEqual(get_occurrences(rule, date(2026, 4, 1), date(2026, 12, 31)), [])


class TestDaily(unittest.TestCase):
    def test_every_n_days(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER, interval=3)
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 1, 10))
        self.assertEqual(got, [date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 7), date(2026, 1, 10)])

    def test_count_is_exact_even_if_window_could_hold_more(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.COUNT, interval=1, count=5)
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(len(got), 5)
        self.assertEqual(got[-1], date(2026, 1, 5))

    def test_end_date_is_exact_and_inclusive(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.END_DATE, interval=1,
                               end_date=date(2026, 3, 31))
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(got[-1], date(2026, 3, 31))
        self.assertNotIn(date(2026, 4, 1), got)


class TestWeekly(unittest.TestCase):
    def test_start_date_not_matching_pattern_shifts_to_first_match(self):
        # 2026-01-02 is a Friday. Pattern is Monday only.
        rule = RecurrenceRule(date(2026, 1, 2), Pattern.WEEKLY, EndType.NEVER, weekdays={0})
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual(got[0], date(2026, 1, 5))  # first Monday on/after the Friday start

    def test_multiple_weekdays_ordered(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.WEEKLY, EndType.NEVER, weekdays={0, 3})
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 1, 14))
        self.assertEqual(got, sorted(got))
        self.assertEqual(len(got), len(set(got)))

    def test_count_is_exact(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.WEEKLY, EndType.COUNT, weekdays={0, 3}, count=3)
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(len(got), 3)
        self.assertEqual(got, [date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 8)])

    def test_end_date_is_exact_and_inclusive(self):
        # Mondays only; end_date lands on a Monday and must be included.
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.WEEKLY, EndType.END_DATE, weekdays={0},
                              end_date=date(2026, 1, 26))
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(got, [date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19), date(2026, 1, 26)])


class TestMonthly(unittest.TestCase):
    def test_month_end_clamps_in_non_leap_february(self):
        rule = RecurrenceRule(date(2023, 1, 31), Pattern.MONTHLY, EndType.NEVER, day_of_month=31)
        got = get_occurrences(rule, date(2023, 1, 1), date(2023, 4, 30))
        self.assertEqual(got, [date(2023, 1, 31), date(2023, 2, 28), date(2023, 3, 31), date(2023, 4, 30)])

    def test_month_end_clamps_in_leap_february(self):
        rule = RecurrenceRule(date(2024, 1, 31), Pattern.MONTHLY, EndType.NEVER, day_of_month=31)
        got = get_occurrences(rule, date(2024, 2, 1), date(2024, 2, 29))
        self.assertEqual(got, [date(2024, 2, 29)])

    def test_start_date_not_matching_pattern_shifts_to_next_month(self):
        # start on the 15th, pattern is "on the 1st" -> 1st already passed this month.
        rule = RecurrenceRule(date(2026, 1, 15), Pattern.MONTHLY, EndType.NEVER, day_of_month=1)
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 3, 31))
        self.assertEqual(got, [date(2026, 2, 1), date(2026, 3, 1)])

    def test_count_is_exact(self):
        rule = RecurrenceRule(date(2026, 1, 31), Pattern.MONTHLY, EndType.COUNT, day_of_month=31, count=3)
        got = get_occurrences(rule, date(2026, 1, 1), date(2027, 12, 31))
        self.assertEqual(len(got), 3)
        self.assertEqual(got, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

    def test_end_date_is_exact_and_inclusive(self):
        rule = RecurrenceRule(date(2026, 1, 15), Pattern.MONTHLY, EndType.END_DATE, day_of_month=15,
                              end_date=date(2026, 3, 15))
        got = get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(got, [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)])


class TestWindowAndDedup(unittest.TestCase):
    def test_window_is_inclusive_on_both_ends(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER, interval=1)
        got = get_occurrences(rule, date(2026, 1, 5), date(2026, 1, 5))
        self.assertEqual(got, [date(2026, 1, 5)])

    def test_invalid_window_raises(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER)
        with self.assertRaises(ValueError):
            get_occurrences(rule, date(2026, 2, 1), date(2026, 1, 1))

    def test_non_date_window_raises_type_error(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER)
        with self.assertRaises(TypeError):
            get_occurrences(rule, "2026-01-01", date(2026, 1, 31))

    def test_non_date_start_date_raises_type_error(self):
        with self.assertRaises(TypeError):
            RecurrenceRule("2026-01-01", Pattern.DAILY, EndType.NEVER)

    def test_datetime_start_date_rejected(self):
        # datetime subclasses date, so it must be rejected explicitly or comparisons crash later.
        with self.assertRaises(TypeError):
            RecurrenceRule(datetime(2026, 1, 1, 9, 0), Pattern.DAILY, EndType.NEVER)

    def test_datetime_window_rejected(self):
        rule = RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER)
        with self.assertRaises(TypeError):
            get_occurrences(rule, datetime(2026, 1, 1, 9, 0), date(2026, 1, 10))


class TestValidation(unittest.TestCase):
    def test_weekly_requires_weekdays(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.WEEKLY, EndType.NEVER)

    def test_weekly_rejects_out_of_range_weekday(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.WEEKLY, EndType.NEVER, weekdays={7})

    def test_monthly_requires_day_of_month(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.MONTHLY, EndType.NEVER)

    def test_count_end_requires_count(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.COUNT)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.COUNT, count=-3)

    def test_daily_interval_below_one_rejected(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.NEVER, interval=0)

    def test_monthly_day_of_month_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.MONTHLY, EndType.NEVER, day_of_month=32)

    def test_end_date_end_requires_end_date(self):
        with self.assertRaises(ValueError):
            RecurrenceRule(date(2026, 1, 1), Pattern.DAILY, EndType.END_DATE)


if __name__ == "__main__":
    unittest.main()

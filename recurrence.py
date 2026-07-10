"""Recurrence engine: expand a RecurrenceRule into concrete date occurrences.

Design decisions worth knowing about:

Month-end behavior (monthly on day 31 in February):
    Clamped to the last valid day of the month (Feb 28, or 29 in a leap year).
    Chosen over "skip the month" because a monthly task should fire exactly
    once per month, so skipping breaks that invariant and silently drops a
    task the user is relying on. Clamping keeps cadence predictable at the
    cost of the date shifting slightly in short months.

Start date that doesn't match the pattern (e.g. weekly on Monday starting on
a Friday, or monthly on the 1st starting on the 15th):
    start_date is the anchor point, not a guaranteed occurrence. The first
    occurrence is the first date >= start_date that satisfies the pattern.
    Only DAILY always includes start_date itself (there's nothing to
    "match", every date is valid for "every N days" starting from day 0).

End condition exactness:
    "after K occurrences" and "until <end_date>" are both evaluated against
    the full occurrence sequence starting from start_date, not against the
    window. A rule capped at 5 occurrences returns at most 5 occurrences
    total, even if the window would otherwise contain more of them.

Window semantics:
    get_occurrences(rule, window_start, window_end) is inclusive on both
    ends.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from calendar import monthrange
from enum import Enum
from typing import Iterator, List, Optional, Set


def _require_plain_date(value, name: str) -> None:
    # datetime is a subclass of date, so reject it explicitly or comparisons crash later.
    if isinstance(value, datetime) or not isinstance(value, date):
        raise TypeError(f"{name} must be a datetime.date (not datetime.datetime)")


class Pattern(Enum):
    ONE_OFF = "one_off"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class EndType(Enum):
    NEVER = "never"
    END_DATE = "end_date"
    COUNT = "count"


@dataclass
class RecurrenceRule:
    start_date: date
    pattern: Pattern
    end_type: EndType
    interval: int = 1                      # DAILY/WEEKLY: every `interval` days/weeks
    weekdays: Optional[Set[int]] = None    # WEEKLY: 0=Mon .. 6=Sun
    day_of_month: Optional[int] = None     # MONTHLY: 1..31, clamped to month length
    end_date: Optional[date] = None        # required if end_type == END_DATE
    count: Optional[int] = None            # required if end_type == COUNT

    def __post_init__(self):
        _require_plain_date(self.start_date, "start_date")
        if self.end_date is not None:
            _require_plain_date(self.end_date, "end_date")
        if self.pattern in (Pattern.DAILY, Pattern.WEEKLY) and self.interval < 1:
            raise ValueError("interval must be >= 1")
        if self.pattern == Pattern.WEEKLY:
            if not self.weekdays:
                raise ValueError("weekly pattern requires a non-empty weekdays set")
            if not all(0 <= d <= 6 for d in self.weekdays):
                raise ValueError("weekdays must be in 0..6 (0=Mon .. 6=Sun)")
        if self.pattern == Pattern.MONTHLY and not (self.day_of_month and 1 <= self.day_of_month <= 31):
            raise ValueError("monthly pattern requires day_of_month in 1..31")
        if self.end_type == EndType.END_DATE and self.end_date is None:
            raise ValueError("end_type=END_DATE requires end_date")
        if self.end_type == EndType.COUNT and (self.count is None or self.count < 1):
            raise ValueError("end_type=COUNT requires count >= 1")


def _add_months(d: date, months: int):
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return year, month


def _clamped_month_date(year: int, month: int, day: int) -> date:
    last_day = monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _raw_occurrences(rule: RecurrenceRule) -> Iterator[date]:
    """Yield occurrences in ascending order, unbounded by any window."""
    if rule.pattern == Pattern.ONE_OFF:
        yield rule.start_date
        return

    if rule.pattern == Pattern.DAILY:
        current = rule.start_date
        while True:
            yield current
            current += timedelta(days=rule.interval)

    elif rule.pattern == Pattern.WEEKLY:
        current = rule.start_date
        anchor = rule.start_date - timedelta(days=rule.start_date.weekday())  # start of the week containing start_date
        while True:
            week_index = (current - anchor).days // 7
            if week_index % rule.interval == 0 and current.weekday() in rule.weekdays:
                yield current
            current += timedelta(days=1)

    elif rule.pattern == Pattern.MONTHLY:
        month_offset = 0
        while True:
            year, month = _add_months(rule.start_date, month_offset)
            candidate = _clamped_month_date(year, month, rule.day_of_month)
            if candidate >= rule.start_date:
                yield candidate
            month_offset += 1

    else:
        raise ValueError(f"unknown pattern: {rule.pattern}")


def get_occurrences(rule: RecurrenceRule, window_start: date, window_end: date) -> List[date]:
    """Return ordered, de-duplicated occurrences of `rule` within [window_start, window_end]."""
    _require_plain_date(window_start, "window_start")
    _require_plain_date(window_end, "window_end")
    if window_start > window_end:
        raise ValueError("window_start must be <= window_end")

    results: List[date] = []
    seen = set()
    emitted = 0

    for occ in _raw_occurrences(rule):
        if rule.end_type == EndType.END_DATE and occ > rule.end_date:
            break

        emitted += 1
        if rule.end_type == EndType.COUNT and emitted > rule.count:
            break

        if occ > window_end:
            break  # sequence is strictly increasing -> nothing left can match

        if occ >= window_start and occ not in seen:
            seen.add(occ)
            results.append(occ)

    return results

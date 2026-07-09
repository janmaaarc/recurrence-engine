# Recurrence Engine

`get_occurrences(rule, window_start, window_end)` expands a `RecurrenceRule`
into concrete date occurrences inside a window (inclusive both ends).

Supports one-off, daily (every N days), weekly (set weekdays), and monthly
(day-of-month) patterns, with never / end-date / after-K-occurrences end
conditions.

## Requirements

Python 3.9+, standard library only. No dependencies.

## Usage

```python
from datetime import date
from recurrence import RecurrenceRule, Pattern, EndType, get_occurrences

# "the 31st of each month, 3 times" clamps in short months
rule = RecurrenceRule(
    start_date=date(2026, 1, 31),
    pattern=Pattern.MONTHLY,
    end_type=EndType.COUNT,
    day_of_month=31,
    count=3,
)
get_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
# [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
```

## Tests

```
python3 -m unittest test_recurrence -v
```

28 tests covering the areas that matter most:

- **Month-end clamping** in leap and non-leap February.
- **Exact termination**: `count` and `end_date` both verified per pattern,
  including that `count` caps the sequence even when the window holds more.
- **Start date that doesn't match the pattern** (weekly and monthly).
- **Window inclusivity and dedup**.
- **Input validation**: rejects `datetime` (a `date` subclass), out-of-range
  weekday and day-of-month, non-positive `count` and `interval`.

## Design decisions (see recurrence.py docstring for detail)

- **Month-end (31st in Feb):** clamps to the last valid day of the month
  (Feb 28/29). A monthly task fires once per month by definition, so
  skipping breaks that invariant.
- **Start date mismatched to pattern:** start_date is an anchor, not a
  guaranteed occurrence. First occurrence is the first date >= start_date
  that satisfies the pattern (only DAILY always includes start_date itself).
- **End conditions (`count` / `end_date`):** evaluated against the full
  sequence from start_date, not against the window, so they stay exact
  regardless of what window you query.

## Limitations (where it could break)

- **Naive dates only.** No time-of-day, timezone, or DST handling. Once
  occurrences carry a clock time, "9am daily" will drift across a DST
  transition unless times are materialized per the timezone plan below.
- **Weekly generation is O(days in window).** It scans day by day, which is
  fine for normal windows but slow for very large ones (decades). Jumping
  straight to the next matching weekday would fix it.
- **No "Nth weekday of month" pattern yet** (the "2nd Tuesday" case). The
  extension plan is documented below but not implemented.

## Extending to "2nd Tuesday of each month" and timezones/DST

- Add a pattern kind that stores `(week_ordinal, weekday)` instead of
  `day_of_month`. Generation becomes: for each month, list all dates whose
  weekday matches, pick the Nth (or last, for ordinal -1). Same clamp
  question applies if the month has fewer than N occurrences of that
  weekday (e.g. "5th Tuesday").
- Timezones/DST: today the engine works entirely in naive `date` objects, so
  it's DST-agnostic. Once occurrences carry a time-of-day, store rule times
  in the task's IANA timezone (not UTC) and materialize to UTC per-occurrence
  at expansion time, using a library like `zoneinfo`. This is what makes
  "9am daily" stay 9am local across a DST transition instead of drifting an
  hour. Naive one-off "add N hours" math breaks on the transition day.

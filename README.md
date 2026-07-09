# Recurrence Engine

`get_occurrences(rule, window_start, window_end)` expands a `RecurrenceRule`
into concrete date occurrences inside a window (inclusive both ends).

## Run tests

```
python3 -m unittest test_recurrence -v
```

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

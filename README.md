# nldate

Parse natural-language date strings into `datetime.date` objects.

```python
from datetime import date
from nldate import parse

parse("5 days before December 1st, 2025")  # 2025-11-26
parse("1 year and 2 months after yesterday", date(2025, 11, 10))  # 2027-01-09
parse("next Tuesday", date(2025, 11, 10))  # 2025-11-11
```

`parse(s, today=None)` uses `today` as the reference for relative expressions
(default: `date.today()`). Unrecognized input, including the empty string,
raises `ValueError`.

## Supported inputs

- **Absolute dates**: `December 1st, 2025`, `Dec. 1 2025`, `1 December 2025`,
  `the first of December, 2025`, `Monday, December 1, 2025`, `2025-12-01`,
  `12/01/2025`, `12/1/25`, `20251201`, `01-Dec-2025`, `December 2025`,
  `December 25` (current year).
- **Keywords**: `today`, `now`, `tomorrow`, `yesterday`,
  `the day after tomorrow`, `the day before yesterday`.
- **Relative offsets**: `in 3 days`, `3 days ago`, `2 weeks from now`,
  `3 days later`, `in a couple of months`, `twenty-one days from today`.
- **Offsets from another date** (recursive): `5 days before December 1st, 2025`,
  `1 year, 2 months, and 3 days after 2025-01-01`, `a week from next Tuesday`,
  `10 business days from today`.
- **Weekdays**: `Friday`, `this Friday`, `next Tuesday`, `last Friday`,
  `Tuesday after next`, `Tuesday next week`, `the first Monday after Dec 2, 2025`.
- **Periods**: `next week`, `last month`, `next year`, `this weekend`,
  `end of the month`, `first day of next month`, `last day of February 2024`,
  `the first Monday of December 2025`, `the last Friday of the month`, `the 15th`.

Units: days, weeks, fortnights, months, years, decades, business days. Numbers
may be digits or words (`a`, `two`, `twenty-one`, `a couple of`). Month
arithmetic clamps to the end of the month (`1 month after January 31` → Feb 28/29).

### Conventions

- `next <weekday>` is the first such day strictly after today; `last <weekday>`
  is the most recent one strictly before today. A bare weekday or
  `this <weekday>` is the upcoming one, counting today.
- Numeric dates like `01/02/2025` are read month-first (US), unless the first
  number is greater than 12.

## Development

```sh
uv run pytest
uv run mypy src/
uv run ruff check
uv run ruff format --check
```

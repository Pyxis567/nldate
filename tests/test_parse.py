from datetime import date

import pytest

from nldate import parse

# Monday, November 10, 2025
TODAY = date(2025, 11, 10)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Absolute dates, many formats
        ("December 1st, 2025", date(2025, 12, 1)),
        ("December 1, 2025", date(2025, 12, 1)),
        ("Dec 1 2025", date(2025, 12, 1)),
        ("Dec. 1, 2025", date(2025, 12, 1)),
        ("1 December 2025", date(2025, 12, 1)),
        ("1st of December, 2025", date(2025, 12, 1)),
        ("the first of December, 2025", date(2025, 12, 1)),
        ("December twenty-first, 2025", date(2025, 12, 21)),
        ("Monday, December 1, 2025", date(2025, 12, 1)),
        ("2025-12-01", date(2025, 12, 1)),
        ("2025/12/01", date(2025, 12, 1)),
        ("12/01/2025", date(2025, 12, 1)),
        ("12/1/25", date(2025, 12, 1)),
        ("31/12/2025", date(2025, 12, 31)),
        ("20251201", date(2025, 12, 1)),
        ("01-Dec-2025", date(2025, 12, 1)),
        ("December 2025", date(2025, 12, 1)),
        ("December 25", date(2025, 12, 25)),
        ("  DECEMBER   1ST,   2025  ", date(2025, 12, 1)),
    ],
)
def test_absolute_dates(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", date(2025, 11, 10)),
        ("now", date(2025, 11, 10)),
        ("tomorrow", date(2025, 11, 11)),
        ("yesterday", date(2025, 11, 9)),
        ("the day after tomorrow", date(2025, 11, 12)),
        ("the day before yesterday", date(2025, 11, 8)),
    ],
)
def test_keywords(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("in 3 days", date(2025, 11, 13)),
        ("in a week", date(2025, 11, 17)),
        ("in two weeks", date(2025, 11, 24)),
        ("3 days ago", date(2025, 11, 7)),
        ("a fortnight ago", date(2025, 10, 27)),
        ("2 weeks from now", date(2025, 11, 24)),
        ("3 days later", date(2025, 11, 13)),
        ("in a couple of months", date(2026, 1, 10)),
        ("twenty-one days from today", date(2025, 12, 1)),
    ],
)
def test_simple_relative(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("1 year and 2 months after yesterday", date(2027, 1, 9)),
        ("two weeks from tomorrow", date(2025, 11, 25)),
        ("1 year, 2 months, and 3 days after 2025-01-01", date(2026, 3, 4)),
        ("a week from next Tuesday", date(2025, 11, 18)),
        ("3 days after the day after tomorrow", date(2025, 11, 15)),
        ("10 business days from today", date(2025, 11, 24)),
    ],
)
def test_offset_from_anchor(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 month after January 31, 2025", date(2025, 2, 28)),
        ("1 month after January 31, 2024", date(2024, 2, 29)),
        ("1 year after February 29, 2024", date(2025, 2, 28)),
        ("1 month before March 31, 2025", date(2025, 2, 28)),
    ],
)
def test_month_arithmetic_clamps_to_month_end(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("next Tuesday", date(2025, 11, 11)),
        ("next Monday", date(2025, 11, 17)),
        ("last Friday", date(2025, 11, 7)),
        ("last Monday", date(2025, 11, 3)),
        ("Friday", date(2025, 11, 14)),
        ("this Friday", date(2025, 11, 14)),
        ("Monday", date(2025, 11, 10)),
        ("Tuesday after next", date(2025, 11, 18)),
        ("Tuesday next week", date(2025, 11, 18)),
        ("the first Monday after December 2, 2025", date(2025, 12, 8)),
    ],
)
def test_weekdays(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("next week", date(2025, 11, 17)),
        ("last week", date(2025, 11, 3)),
        ("next month", date(2025, 12, 10)),
        ("next year", date(2026, 11, 10)),
        ("end of the month", date(2025, 11, 30)),
        ("first day of next month", date(2025, 12, 1)),
        ("last day of February 2024", date(2024, 2, 29)),
        ("the first Monday of December 2025", date(2025, 12, 1)),
        ("the last Friday of November 2025", date(2025, 11, 28)),
        ("the 15th", date(2025, 11, 15)),
    ],
)
def test_periods_and_boundaries(text: str, expected: date) -> None:
    assert parse(text, TODAY) == expected


@pytest.mark.parametrize(
    "text",
    ["", "   ", "hello world", "banana days ago", "February 30, 2025", "13/13/2025"],
)
def test_invalid_input_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, TODAY)


def test_today_defaults_to_current_date() -> None:
    assert parse("today") == date.today()


def test_case_and_punctuation_insensitive() -> None:
    assert parse("NEXT TUESDAY.", TODAY) == parse("next tuesday", TODAY)

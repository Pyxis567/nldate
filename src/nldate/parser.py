"""Turn natural-language date strings into ``datetime.date`` objects."""

from __future__ import annotations

import calendar
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tues": 1,
    "tue": 1,
    "wednesday": 2,
    "weds": 2,
    "wed": 2,
    "thursday": 3,
    "thurs": 3,
    "thur": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

ONES: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

ORDINAL_ONES: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
}

ORDINAL_TENS: dict[str, int] = {"twentieth": 20, "thirtieth": 30}


def _build_ordinal_words() -> dict[str, int]:
    words = dict(ORDINAL_ONES)
    words.update(ORDINAL_TENS)
    for tens_word, tens_val in (("twenty", 20), ("thirty", 30)):
        for ones_word, ones_val in ORDINAL_ONES.items():
            if ones_val >= 10:
                continue
            for sep in ("-", " "):
                words[f"{tens_word}{sep}{ones_word}"] = tens_val + ones_val
    return words


ORDINAL_WORDS: dict[str, int] = _build_ordinal_words()


def _alternation(words: Mapping[str, int]) -> str:
    """Regex alternation of words, longest first so 'sept' beats 'sep'."""
    keys = sorted(words, key=len, reverse=True)
    return "|".join(re.escape(k) for k in keys)


MONTH_RE = rf"(?P<month>{_alternation(MONTHS)})"
WEEKDAY_RE = rf"(?P<weekday>{_alternation(WEEKDAYS)})"
DAY_RE = rf"(?P<day>\d{{1,2}}(?:st|nd|rd|th)?|{_alternation(ORDINAL_WORDS)})"
YEAR_RE = r"(?P<year>\d{4}|'\d{2})"

UNIT_RE = (
    r"(?P<unit>business\s+days?|work\s*days?|weekdays?|days?|weeks?|"
    r"fortnights?|months?|years?|yrs?|decades?|centuries|century)"
)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    """Add (or subtract) months, clamping the day to the end of the month."""
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    if year < 1 or year > 9999:
        raise ValueError("resulting date is out of range")
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_business_days(d: date, n: int) -> date:
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining:
        d += timedelta(days=step)
        if d.weekday() < 5:
            remaining -= 1
    return d


def _parse_number(text: str) -> int | None:
    """Parse '3', 'three', 'twenty-one', 'a', 'a couple of', etc."""
    t = text.strip()
    if re.fullmatch(r"\d+", t):
        return int(t)
    if t in ("a", "an", "one", "a single", "single"):
        return 1
    if re.fullmatch(r"(?:a\s+)?couple(?:\s+of)?", t):
        return 2
    if t in ONES:
        return ONES[t]
    if t in TENS:
        return TENS[t]
    m = re.fullmatch(r"(\w+)[\s-](\w+)", t)
    if m and m.group(1) in TENS and m.group(2) in ONES and ONES[m.group(2)] < 10:
        return TENS[m.group(1)] + ONES[m.group(2)]
    if t == "a dozen" or t == "dozen":
        return 12
    return None


def _parse_day(text: str) -> int:
    text = text.strip()
    if text in ORDINAL_WORDS:
        return ORDINAL_WORDS[text]
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", text)
    if not m:
        raise ValueError(f"unrecognized day: {text!r}")
    return int(m.group(1))


def _parse_year(text: str | None, today: date) -> int:
    if text is None:
        return today.year
    if text.startswith("'"):
        return 2000 + int(text[1:])
    return int(text)


def _expand_year(y: int) -> int:
    return 2000 + y if y < 100 else y


def _next_weekday(start: date, weekday: int, *, inclusive: bool) -> date:
    """First date >= start (inclusive) or > start with the given weekday."""
    delta = (weekday - start.weekday()) % 7
    if delta == 0 and not inclusive:
        delta = 7
    return start + timedelta(days=delta)


def _prev_weekday(start: date, weekday: int, *, inclusive: bool) -> date:
    delta = (start.weekday() - weekday) % 7
    if delta == 0 and not inclusive:
        delta = 7
    return start - timedelta(days=delta)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    t = s.strip().lower()
    t = t.replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.!?]+$", "", t)  # trailing punctuation
    t = re.sub(r"(?<=[a-z])\.", "", t)  # abbreviations: "dec." -> "dec"
    t = re.sub(r"\s*,\s*", ", ", t)
    t = t.strip(" ,")
    t = re.sub(r"^(?:on|by|for|until|till|due)\s+", "", t)
    return t


# ---------------------------------------------------------------------------
# Durations: "1 year and 2 months", "three weeks", "a fortnight"
# ---------------------------------------------------------------------------

Duration = tuple[int, int, int]  # (months, days, business_days)


def _parse_duration(text: str) -> Duration | None:
    text = text.strip()
    if not text:
        return None
    parts = re.split(r"\s*(?:,\s*and|,|\band\b|\bplus\b|&)\s*", text)
    months = days = bdays = 0
    for part in parts:
        part = part.strip()
        if not part:
            return None
        m = re.fullmatch(rf"(?P<num>.+?)\s*{UNIT_RE}", part)
        if not m:
            return None
        n = _parse_number(m.group("num"))
        if n is None:
            return None
        unit = re.sub(r"\s+", " ", m.group("unit"))
        if unit.startswith(("business", "work", "weekday")):
            bdays += n
        elif unit.startswith("day"):
            days += n
        elif unit.startswith("fortnight"):
            days += 14 * n
        elif unit.startswith("week"):
            days += 7 * n
        elif unit.startswith("month"):
            months += n
        elif unit.startswith(("year", "yr")):
            months += 12 * n
        elif unit.startswith("decade"):
            months += 120 * n
        elif unit.startswith("centur"):
            months += 1200 * n
        else:  # pragma: no cover - UNIT_RE guarantees one of the above
            return None
    return months, days, bdays


def _apply_duration(d: date, dur: Duration, sign: int) -> date:
    months, days, bdays = dur
    d = _add_months(d, sign * months)
    d += timedelta(days=sign * days)
    if bdays:
        d = _add_business_days(d, sign * bdays)
    return d


BEFORE_WORDS = ("before", "prior to", "earlier than", "preceding")
AFTER_WORDS = ("after", "from", "following", "later than")


def _parse_relative_to_anchor(text: str, today: date) -> date | None:
    """'<duration> before/after/from <date expression>'."""
    words = [(w, -1) for w in BEFORE_WORDS] + [(w, 1) for w in AFTER_WORDS]
    pattern = "|".join(re.escape(w) for w, _ in words)
    signs = dict(words)
    for m in re.finditer(rf"\s(?P<dir>{pattern})\s", f" {text} "):
        dur_text = text[: m.start()].strip()
        anchor_text = text[m.end() - 1 :].strip()
        dur = _parse_duration(dur_text)
        if dur is None:
            continue
        anchor = _parse_expr(anchor_text, today)
        if anchor is None:
            continue
        return _apply_duration(anchor, dur, signs[m.group("dir")])
    return None


def _parse_simple_relative(text: str, today: date) -> date | None:
    """'in 3 days', '3 days ago', '2 weeks from now', '5 days later'."""
    m = re.fullmatch(r"(?:in|within|after)\s+(.+?)(?:'s?\s+time|\s+time)?", text)
    if m:
        dur = _parse_duration(m.group(1))
        if dur is not None:
            return _apply_duration(today, dur, 1)
    m = re.fullmatch(r"(.+?)\s+(ago|back|earlier|before|previously)", text)
    if m:
        dur = _parse_duration(m.group(1))
        if dur is not None:
            return _apply_duration(today, dur, -1)
    m = re.fullmatch(r"(.+?)\s+(from now|hence|later|from today|after today|out)", text)
    if m:
        dur = _parse_duration(m.group(1))
        if dur is not None:
            return _apply_duration(today, dur, 1)
    # "+3 days", "-2 weeks"
    m = re.fullmatch(r"([+-])\s*(.+)", text)
    if m:
        dur = _parse_duration(m.group(2))
        if dur is not None:
            return _apply_duration(today, dur, 1 if m.group(1) == "+" else -1)
    return None


# ---------------------------------------------------------------------------
# Keywords and relative periods
# ---------------------------------------------------------------------------

KEYWORDS: dict[str, int] = {
    "today": 0,
    "now": 0,
    "right now": 0,
    "tonight": 0,
    "this morning": 0,
    "this afternoon": 0,
    "this evening": 0,
    "todays date": 0,
    "today's date": 0,
    "tomorrow": 1,
    "tmrw": 1,
    "tmr": 1,
    "tomorrow morning": 1,
    "tomorrow night": 1,
    "tomorrow evening": 1,
    "yesterday": -1,
    "yesterday morning": -1,
    "last night": -1,
    "the day after tomorrow": 2,
    "day after tomorrow": 2,
    "overmorrow": 2,
    "the day before yesterday": -2,
    "day before yesterday": -2,
}


def _parse_keyword(text: str, today: date) -> date | None:
    if text in KEYWORDS:
        return today + timedelta(days=KEYWORDS[text])
    return None


def _shift_for(modifier: str) -> int | None:
    if modifier in ("next", "following", "coming", "upcoming"):
        return 1
    if modifier in ("last", "previous", "past", "prior"):
        return -1
    if modifier in ("this", "the", "current"):
        return 0
    return None


PERIOD_MOD = (
    r"(?P<mod>next|following|coming|upcoming|last|previous|past|prior|this|the|current)"
)


def _parse_period(text: str, today: date) -> date | None:
    """'next week', 'last month', 'next year', 'this weekend'."""
    m = re.fullmatch(rf"{PERIOD_MOD}\s+(?P<period>week|month|year|weekend)", text)
    if m:
        shift = _shift_for(m.group("mod"))
        assert shift is not None
        period = m.group("period")
        if period == "week":
            return today + timedelta(days=7 * shift)
        if period == "month":
            return _add_months(today, shift)
        if period == "year":
            return _add_months(today, 12 * shift)
        # weekend -> Saturday
        if shift == 0:
            if today.weekday() == 6:
                return today - timedelta(days=1)
            return _next_weekday(today, 5, inclusive=True)
        sat = _next_weekday(today, 5, inclusive=True)
        if shift < 0:
            return _prev_weekday(today, 5, inclusive=False)
        return sat + timedelta(days=7) if today.weekday() >= 5 else sat
    return None


def _resolve_period_ref(text: str, today: date) -> tuple[str, date] | None:
    """Resolve 'the month', 'next month', 'december 2025', '2026' to (kind, date).

    kind is 'week', 'month', or 'year'; the date is any day inside that period.
    """
    m = re.fullmatch(rf"{PERIOD_MOD}\s+(?P<period>week|month|year)", text)
    if m:
        shift = _shift_for(m.group("mod"))
        assert shift is not None
        period = m.group("period")
        if period == "week":
            return "week", today + timedelta(days=7 * shift)
        if period == "month":
            return "month", _add_months(today.replace(day=1), shift)
        return "year", date(today.year + shift, 1, 1)
    m = re.fullmatch(rf"{MONTH_RE}(?:,?\s+{YEAR_RE})?", text)
    if m:
        year = _parse_year(m.group("year"), today)
        return "month", date(year, MONTHS[m.group("month")], 1)
    m = re.fullmatch(r"(\d{4})", text)
    if m:
        return "year", date(int(m.group(1)), 1, 1)
    return None


def _parse_boundary(text: str, today: date) -> date | None:
    """'end of the month', 'first day of next month', 'last day of 2025'."""
    m = re.fullmatch(
        r"(?:the\s+)?(?P<edge>end|start|beginning|first\s+day|last\s+day)\s+of\s+(?P<ref>.+)",
        text,
    )
    if not m:
        return None
    ref = _resolve_period_ref(m.group("ref"), today)
    if ref is None:
        return None
    kind, d = ref
    first = m.group("edge") in ("start", "beginning", "first day")
    if kind == "week":
        start = _week_start(d)
        return start if first else start + timedelta(days=6)
    if kind == "month":
        if first:
            return d.replace(day=1)
        return d.replace(day=calendar.monthrange(d.year, d.month)[1])
    return date(d.year, 1, 1) if first else date(d.year, 12, 31)


ORDINAL_POS: dict[str, int] = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
    "last": -1,
}


def _parse_nth_weekday(text: str, today: date) -> date | None:
    """'the first monday of december 2025', 'last friday of the month'."""
    m = re.fullmatch(
        rf"(?:the\s+)?(?P<n>{_alternation(ORDINAL_POS)})\s+{WEEKDAY_RE}\s+(?:of|in)\s+(?P<ref>.+)",
        text,
    )
    if not m:
        return None
    ref = _resolve_period_ref(m.group("ref"), today)
    if ref is None or ref[0] != "month":
        return None
    first_of_month = ref[1]
    wd = WEEKDAYS[m.group("weekday")]
    n = ORDINAL_POS[m.group("n")]
    if n > 0:
        d = _next_weekday(first_of_month, wd, inclusive=True) + timedelta(weeks=n - 1)
        if d.month != first_of_month.month:
            raise ValueError(f"there is no such weekday in that month: {text!r}")
        return d
    last = first_of_month.replace(
        day=calendar.monthrange(first_of_month.year, first_of_month.month)[1]
    )
    return _prev_weekday(last, wd, inclusive=True)


def _parse_weekday(text: str, today: date) -> date | None:
    """'tuesday', 'next tuesday', 'last friday', 'tuesday after next'."""
    m = re.fullmatch(
        rf"(?:(?P<mod>next|this|coming|upcoming|last|previous|past|prior)\s+)?{WEEKDAY_RE}",
        text,
    )
    if m:
        wd = WEEKDAYS[m.group("weekday")]
        mod = m.group("mod")
        if mod in ("last", "previous", "past", "prior"):
            return _prev_weekday(today, wd, inclusive=False)
        if mod in ("next", "coming", "upcoming"):
            return _next_weekday(today, wd, inclusive=False)
        # bare weekday or "this <weekday>": the upcoming one, today included
        return _next_weekday(today, wd, inclusive=True)

    m = re.fullmatch(rf"{WEEKDAY_RE}\s+after\s+next", text)
    if m:
        wd = WEEKDAYS[m.group("weekday")]
        return _next_weekday(today, wd, inclusive=False) + timedelta(days=7)
    m = re.fullmatch(rf"{WEEKDAY_RE}\s+before\s+last", text)
    if m:
        wd = WEEKDAYS[m.group("weekday")]
        return _prev_weekday(today, wd, inclusive=False) - timedelta(days=7)

    # "tuesday of next week", "next week tuesday", "tuesday this week"
    m = re.fullmatch(
        rf"{WEEKDAY_RE}\s+(?:of\s+)?(?P<mod>next|this|last|the\s+following|the\s+previous)\s+week",
        text,
    ) or re.fullmatch(
        rf"(?P<mod>next|this|last)\s+week(?:\s+on)?\s+{WEEKDAY_RE}",
        text,
    )
    if m:
        mod = m.group("mod").replace("the ", "")
        shift = _shift_for(mod)
        assert shift is not None
        wd = WEEKDAYS[m.group("weekday")]
        return _week_start(today) + timedelta(days=7 * shift + wd)

    # "the first tuesday after december 1, 2025", "friday before christmas"
    m = re.fullmatch(
        rf"(?:the\s+)?(?:first\s+)?{WEEKDAY_RE}\s+(?P<dir>after|before|following|preceding)\s+(?P<anchor>.+)",
        text,
    )
    if m:
        anchor = _parse_expr(m.group("anchor"), today)
        if anchor is None:
            return None
        wd = WEEKDAYS[m.group("weekday")]
        if m.group("dir") in ("after", "following"):
            return _next_weekday(anchor, wd, inclusive=False)
        return _prev_weekday(anchor, wd, inclusive=False)
    return None


# ---------------------------------------------------------------------------
# Absolute dates
# ---------------------------------------------------------------------------


def _strip_leading_weekday(text: str) -> str:
    m = re.match(rf"{WEEKDAY_RE}(?:,\s*|\s+)(?:the\s+)?(?P<rest>.+)", text)
    if m and m.group("rest"):
        return m.group("rest")
    return text


def _parse_numeric(text: str) -> date | None:
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})", text)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), _expand_year(int(m.group(3)))
        # US convention (month first) unless that is impossible.
        if a > 12 >= b:
            return date(y, b, a)
        return date(y, a, b)
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _parse_month_name(text: str, today: date) -> date | None:
    # Treat hyphens/slashes between tokens as spaces: "01-dec-2025".
    t = re.sub(r"(?<=[a-z0-9])[-/](?=[a-z0-9'])", " ", text)
    # ...but keep hyphenated ordinal words like "twenty-first" intact.
    t = re.sub(
        r"\b(twenty|thirty) (?=first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)",
        r"\1-",
        t,
    )
    t = re.sub(r"\s+of\s+the\s+year\s+", " ", t)

    patterns = [
        rf"{MONTH_RE}\s+(?:the\s+)?{DAY_RE}(?:,?\s+{YEAR_RE})?",
        rf"(?:the\s+)?{DAY_RE}\s+(?:of\s+|day\s+of\s+)?{MONTH_RE}(?:,?\s+{YEAR_RE})?",
        rf"{YEAR_RE},?\s+{MONTH_RE}\s+{DAY_RE}",
    ]
    for p in patterns:
        m = re.fullmatch(p, t)
        if m:
            year = _parse_year(m.group("year"), today)
            return date(year, MONTHS[m.group("month")], _parse_day(m.group("day")))

    # "december 2025" -> first of the month
    m = re.fullmatch(rf"{MONTH_RE},?\s+(?P<year>\d{{4}})", t)
    if m:
        return date(int(m.group("year")), MONTHS[m.group("month")], 1)
    return None


def _parse_day_of_month(text: str, today: date) -> date | None:
    """'the 15th', 'the 3rd of next month'."""
    m = re.fullmatch(
        rf"(?:the\s+)?(?P<day>\d{{1,2}}(?:st|nd|rd|th)|{_alternation(ORDINAL_WORDS)})"
        rf"(?:\s+of\s+(?P<ref>(?:this|next|last|the)\s+month))?",
        text,
    )
    if not m:
        return None
    if (
        not text.startswith("the")
        and m.group("ref") is None
        and not re.search(r"\d", m.group("day"))
    ):
        # Bare ordinal words like "second" are too ambiguous on their own.
        return None
    base = today.replace(day=1)
    if m.group("ref"):
        ref = _resolve_period_ref(m.group("ref"), today)
        assert ref is not None
        base = ref[1]
    return base.replace(day=_parse_day(m.group("day")))


def _parse_absolute(text: str, today: date) -> date | None:
    t = _strip_leading_weekday(text)
    for candidate in (text, t) if t != text else (text,):
        result = _parse_numeric(candidate) or _parse_month_name(candidate, today)
        if result is not None:
            return result
    try:
        return datetime.fromisoformat(text.upper()).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------


def _parse_expr(text: str, today: date) -> date | None:
    text = text.strip(" ,")
    if not text:
        return None
    text = re.sub(r"^(?:on|by)\s+", "", text)
    for handler in (
        _parse_keyword,
        _parse_period,
        _parse_weekday,
        _parse_boundary,
        _parse_nth_weekday,
        _parse_simple_relative,
        _parse_relative_to_anchor,
        _parse_absolute,
        _parse_day_of_month,
    ):
        result = handler(text, today)
        if result is not None:
            return result
    return None


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural-language date string into a ``datetime.date``.

    ``today`` is the reference point for relative expressions such as
    "next Tuesday" or "in 3 days"; it defaults to the current date.

    Raises ``ValueError`` if the string is not a recognized date.
    """
    if today is None:
        today = date.today()
    text = _normalize(s)
    if not text:
        raise ValueError("empty date string")
    try:
        result = _parse_expr(text, today)
    except (OverflowError, IndexError) as exc:
        raise ValueError(f"could not parse date: {s!r}") from exc
    if result is None:
        raise ValueError(f"could not parse date: {s!r}")
    return result

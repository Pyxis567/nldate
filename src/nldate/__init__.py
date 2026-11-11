"""nldate: parse natural-language date strings into ``datetime.date`` objects."""

import sys
from datetime import date

from nldate.parser import parse

__all__ = ["main", "parse"]


def main() -> None:
    """Command-line entry point: ``nldate "next tuesday"``."""
    text = " ".join(sys.argv[1:])
    try:
        print(parse(text, date.today()).isoformat())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

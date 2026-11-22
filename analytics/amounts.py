"""Parse a financing amount out of free text.

Shared by the backend query parser and the Streamlit client so both read the
same number from the same prompt.

A number only counts as an amount when it carries a currency marker
(``€``, ``eur``, ``euro``) or a magnitude suffix (``k``, ``m``, ``mln``,
``million``, ``mila``, ``milioni`` ...). Bare numbers are ignored, so a year
such as "2025" is never read as a loan amount.
"""

from __future__ import annotations

import re

_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "mila": 1_000,
    "m": 1_000_000,
    "mm": 1_000_000,
    "mln": 1_000_000,
    "mio": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "milione": 1_000_000,
    "milioni": 1_000_000,
}

_AMOUNT_RE = re.compile(
    r"(?P<cur>€|\beur\b|\beuro\b)?\s*"
    r"(?P<num>\d[\d.,]*)"
    r"(?:\s*(?P<suf>k|mm|mln|mio|millions|million|milioni|milione|mila|thousand|m)\b)?"
    r"(?:\s*(?P<tcur>€|eur\b|euro\b))?",
    re.IGNORECASE,
)

_THOUSANDS_GROUPED = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")

# A currency-marked number below this is read as thousands ("€750" -> 750k),
# matching the demo convenience the parser has always offered.
_SMALL_AMOUNT_THRESHOLD = 10_000


def _to_float(raw: str) -> float | None:
    """Read 750,000 / 750.000 / 1.5 / 1,5 / 1.234,56 as a float."""
    s = raw.strip(".,")
    if not s:
        return None
    if _THOUSANDS_GROUPED.match(s):
        s = s.replace(".", "").replace(",", "")
    elif "." in s and "," in s:
        decimal = "." if s.rfind(".") > s.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        s = s.replace(thousands, "").replace(decimal, ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_amount(text: str | None) -> int | None:
    """Return the first financing amount in ``text`` in euros, or None."""
    if not text:
        return None
    for match in _AMOUNT_RE.finditer(text):
        cur = match.group("cur") or match.group("tcur")
        suf = (match.group("suf") or "").lower()
        if not cur and not suf:
            continue
        value = _to_float(match.group("num"))
        if value is None or value <= 0:
            continue
        if suf:
            value *= _MULTIPLIERS[suf]
        elif value < _SMALL_AMOUNT_THRESHOLD:
            value *= 1_000
        return int(round(value))
    return None

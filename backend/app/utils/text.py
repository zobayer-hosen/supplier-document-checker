"""Small text and number helpers shared by parsers, evidence checks and rules."""

import re
from decimal import Decimal, InvalidOperation

# Matches numbers such as "12,000", "472.00", "0.5" and "5,664,000.00".
NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")

_CHARACTER_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
}


def normalize_text(text: str) -> str:
    """Lower-case the text, unify quotes/dashes and collapse all whitespace.

    PDF text often breaks one sentence over several lines, so comparing
    normalized text lets a quote match even when line breaks differ.
    """
    for original, replacement in _CHARACTER_REPLACEMENTS.items():
        text = text.replace(original, replacement)
    return re.sub(r"\s+", " ", text).strip().casefold()


def parse_decimal(value: str | None) -> Decimal | None:
    """Turn "5,664,000.00" into Decimal("5664000.00"). Returns None if not a number."""
    if value is None:
        return None
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def find_numbers(text: str) -> list[Decimal]:
    """Return every number written in the text, in order."""
    numbers = (parse_decimal(match) for match in NUMBER_PATTERN.findall(text))
    return [number for number in numbers if number is not None]


def contains_phrase(text: str, phrase: str) -> bool:
    """True when `phrase` appears in `text` as whole words (case-insensitive)."""
    pattern = r"(?<!\w)" + re.escape(normalize_text(phrase)) + r"(?!\w)"
    return re.search(pattern, normalize_text(text)) is not None

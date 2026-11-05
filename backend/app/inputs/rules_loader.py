"""Read the company-rules Markdown file and confirm it matches our rule engine.

The Markdown is NOT turned into code and is never given to the LLM. We only
use it to:
1. Show the reviewer the original wording of each rule.
2. Stop early if the uploaded rules do not match what the Python rule
   engine implements (for example someone changed "20%" to "30%").
"""

import hashlib
import re
from dataclasses import dataclass, field

from app.utils.text import normalize_text
from app.validators.rule_catalog import PENALTY_NOTE_KEYWORDS, RULES


class CompanyRulesError(ValueError):
    """The rules file cannot be used. The message explains why."""


@dataclass
class LoadedRules:
    sha256: str
    rule_text_by_code: dict[str, str] = field(default_factory=dict)


def _section_name(heading: str) -> str | None:
    heading = heading.casefold()
    if "reject" in heading:
        return "reject"
    if "person" in heading or "review" in heading:
        return "review"
    if "note" in heading:
        return "notes"
    return None


def split_rule_lines(markdown: str) -> dict[str, list[str]]:
    """Group the list items ("1. ..." or "- ...") under their section heading."""
    sections: dict[str, list[str]] = {"reject": [], "review": [], "notes": []}
    current: str | None = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            current = _section_name(stripped.lstrip("#").strip())
            continue
        item = re.match(r"^(?:\d+[.)]|[-*])\s+(.*)$", stripped)
        if current and item:
            sections[current].append(item.group(1).strip())
    return sections


def _find_line(lines: list[str], keywords: tuple[str, ...], already_used: set[str]) -> str | None:
    for line in lines:
        text = normalize_text(line)
        if line not in already_used and all(keyword in text for keyword in keywords):
            return line
    return None


def load_company_rules(content: bytes) -> LoadedRules:
    """Check the Markdown file and return the original wording of each rule."""
    try:
        markdown = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CompanyRulesError("The company rules file must be UTF-8 text.") from error

    sections = split_rule_lines(markdown)
    loaded = LoadedRules(sha256=hashlib.sha256(content).hexdigest())
    used_lines: set[str] = set()
    missing: list[str] = []

    for rule in RULES:
        line = _find_line(sections[rule.section], rule.markdown_keywords, used_lines)
        if line is None:
            missing.append(f"{rule.code} ({rule.title})")
            continue
        used_lines.add(line)
        loaded.rule_text_by_code[rule.code] = line

    penalty_note = _find_line(sections["notes"], PENALTY_NOTE_KEYWORDS, set())
    if penalty_note is None:
        missing.append("penalty threshold note (at least 0.5% of order value per week)")
    else:
        loaded.rule_text_by_code["R03"] += " " + penalty_note

    if missing:
        raise CompanyRulesError(
            "The company rules file does not match the rules this system implements. "
            "Could not find: " + "; ".join(missing) + "."
        )
    return loaded

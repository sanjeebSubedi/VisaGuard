from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RedactionResult:
    text: str
    replacements: list[dict[str, str]]


PATTERNS: list[tuple[str, str]] = [
    (r"(?im)^(\s*student name:\s*).+$", r"\1[REDACTED_NAME]"),
    (r"(?im)^(\s*sevis id:\s*).+$", r"\1[REDACTED_SEVIS_ID]"),
    (r"(?im)^(\s*a-number:\s*).+$", r"\1[REDACTED_A_NUMBER]"),
    (r"(?im)^(\s*date of birth:\s*).+$", r"\1[REDACTED_DOB]"),
    (r"(?im)^(\s*address:\s*).+$", r"\1[REDACTED_ADDRESS]"),
    (r"(?im)^(\s*phone:\s*).+$", r"\1[REDACTED_PHONE]"),
    (r"[\w.+-]+@[\w.-]+", "[REDACTED_EMAIL]"),
]


def redact_direct_identifiers(text: str) -> RedactionResult:
    redacted_text = text
    replacements: list[dict[str, str]] = []
    for pattern, replacement in PATTERNS:
        updated_text, count = re.subn(pattern, replacement, redacted_text)
        if count:
            replacements.append({"pattern": pattern, "replacement": replacement, "count": str(count)})
        redacted_text = updated_text
    return RedactionResult(text=redacted_text, replacements=replacements)

from __future__ import annotations

from datetime import date


def require_fields(values: dict[str, object], *field_names: str) -> list[str]:
    missing: list[str] = []
    for field_name in field_names:
        value = values.get(field_name)
        if value is None:
            missing.append(field_name)
    return missing


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)

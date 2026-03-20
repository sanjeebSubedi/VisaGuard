from __future__ import annotations


def require_fields(values: dict[str, object], *field_names: str) -> list[str]:
    missing: list[str] = []
    for field_name in field_names:
        value = values.get(field_name)
        if value is None:
            missing.append(field_name)
    return missing

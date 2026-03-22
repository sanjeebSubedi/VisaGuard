from __future__ import annotations

from dataclasses import dataclass

from app.services.timeline.prerequisites import require_fields


@dataclass(slots=True)
class ConditionalClockStatus:
    status: str
    missing_prerequisites: list[str]


def classify_conditional_clock(
    *,
    facts: dict[str, str],
    trigger_fields: tuple[str, ...],
    required_fields: tuple[str, ...],
) -> ConditionalClockStatus:
    triggered = any(facts.get(field) not in (None, "") for field in trigger_fields)
    if not triggered:
        return ConditionalClockStatus(status="not_applicable", missing_prerequisites=[])

    missing = require_fields(facts, *required_fields)
    if missing:
        return ConditionalClockStatus(status="insufficient_data", missing_prerequisites=missing)

    return ConditionalClockStatus(status="ready", missing_prerequisites=[])

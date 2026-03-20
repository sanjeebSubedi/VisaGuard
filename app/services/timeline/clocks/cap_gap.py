from __future__ import annotations

from app.services.timeline.prerequisites import parse_iso_date, require_fields
from app.services.timeline.types import ClockResult


def evaluate_cap_gap(*, facts: dict[str, str], evaluation_date: str) -> ClockResult:
    missing = require_fields(facts, "cap_gap_end_date")
    if missing:
        return ClockResult(status="insufficient_data", missing_prerequisites=missing)

    end_date = parse_iso_date(facts["cap_gap_end_date"])
    current = parse_iso_date(evaluation_date)
    days_remaining = (end_date - current).days
    status = "active" if days_remaining >= 0 else "completed"

    return ClockResult(
        status=status,
        relevant_dates={"cap_gap_end": facts["cap_gap_end_date"]},
        days_remaining=days_remaining,
    )

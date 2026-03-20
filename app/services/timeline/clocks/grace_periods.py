from __future__ import annotations

from datetime import timedelta

from app.services.timeline.prerequisites import parse_iso_date, require_fields
from app.services.timeline.types import ClockResult


def evaluate_grace_period(*, facts: dict[str, str], evaluation_date: str) -> ClockResult:
    missing = require_fields(facts, "program_end_date")
    if missing:
        return ClockResult(status="insufficient_data", missing_prerequisites=missing)

    program_end = parse_iso_date(facts["program_end_date"])
    grace_end = program_end + timedelta(days=60)
    current = parse_iso_date(evaluation_date)
    days_remaining = (grace_end - current).days
    status = "active" if days_remaining >= 0 else "completed"

    return ClockResult(
        status=status,
        relevant_dates={
            "program_end_date": facts["program_end_date"],
            "grace_period_end": grace_end.isoformat(),
        },
        days_remaining=days_remaining,
    )

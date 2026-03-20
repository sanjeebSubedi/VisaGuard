from __future__ import annotations

from datetime import timedelta

from app.services.timeline.prerequisites import parse_iso_date, require_fields
from app.services.timeline.types import ClockResult


def evaluate_reporting_windows(*, facts: dict[str, str], evaluation_date: str) -> ClockResult:
    missing = require_fields(facts, "start_date")
    if missing:
        return ClockResult(status="insufficient_data", missing_prerequisites=missing)

    trigger = parse_iso_date(facts["start_date"])
    deadline = trigger + timedelta(days=10)
    current = parse_iso_date(evaluation_date)
    days_remaining = (deadline - current).days
    status = "active" if days_remaining >= 0 else "completed"

    return ClockResult(
        status=status,
        relevant_dates={
            "trigger_date": facts["start_date"],
            "report_deadline": deadline.isoformat(),
        },
        days_remaining=days_remaining,
    )

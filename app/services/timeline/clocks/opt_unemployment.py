from __future__ import annotations

from app.services.timeline.prerequisites import parse_iso_date, require_fields
from app.services.timeline.types import ClockResult


def evaluate_opt_unemployment(*, facts: dict[str, str], evaluation_date: str) -> ClockResult:
    missing = require_fields(facts, "card_start_date", "start_date")
    if missing:
        return ClockResult(status="insufficient_data", missing_prerequisites=missing)

    card_start = parse_iso_date(facts["card_start_date"])
    employment_start = parse_iso_date(facts["start_date"])
    days_used = max(0, (employment_start - card_start).days)
    days_remaining = max(0, 90 - days_used)

    return ClockResult(
        status="active",
        relevant_dates={
            "card_start_date": facts["card_start_date"],
            "employment_start_date": facts["start_date"],
        },
        days_remaining=days_remaining,
        limit_days=90,
    )

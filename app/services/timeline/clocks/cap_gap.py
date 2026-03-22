from __future__ import annotations

from app.services.timeline.conditional import classify_conditional_clock
from app.services.timeline.prerequisites import parse_iso_date
from app.services.timeline.types import ClockResult


def evaluate_cap_gap(*, facts: dict[str, str], evaluation_date: str) -> ClockResult:
    classification = classify_conditional_clock(
        facts=facts,
        trigger_fields=("has_cap_gap_extension", "cap_gap_end_date"),
        required_fields=("cap_gap_end_date",),
    )
    if classification.status == "not_applicable":
        return ClockResult(status="not_applicable")
    if classification.status == "insufficient_data":
        return ClockResult(
            status="insufficient_data",
            missing_prerequisites=classification.missing_prerequisites,
        )

    end_date = parse_iso_date(facts["cap_gap_end_date"])
    current = parse_iso_date(evaluation_date)
    days_remaining = (end_date - current).days
    status = "active" if days_remaining >= 0 else "completed"

    return ClockResult(
        status=status,
        relevant_dates={"cap_gap_end": facts["cap_gap_end_date"]},
        days_remaining=days_remaining,
    )

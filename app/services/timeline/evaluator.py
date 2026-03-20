from __future__ import annotations

from app.services.timeline.actions import build_risk_flags_and_actions
from app.services.timeline.clocks import (
    evaluate_cap_gap,
    evaluate_grace_period,
    evaluate_opt_unemployment,
    evaluate_reporting_windows,
    evaluate_stem_opt_unemployment,
)
from app.services.timeline.types import DeadlineItem, TimelineInputs, TimelineStatus


def evaluate_timeline(*, facts: dict[str, str], evaluation_date: str) -> dict[str, object]:
    clocks = {
        "opt_unemployment": evaluate_opt_unemployment(facts=facts, evaluation_date=evaluation_date),
        "stem_opt_unemployment": evaluate_stem_opt_unemployment(facts=facts, evaluation_date=evaluation_date),
        "reporting_windows": evaluate_reporting_windows(facts=facts, evaluation_date=evaluation_date),
        "grace_period": evaluate_grace_period(facts=facts, evaluation_date=evaluation_date),
        "cap_gap": evaluate_cap_gap(facts=facts, evaluation_date=evaluation_date),
    }
    risk_flags, action_items = build_risk_flags_and_actions(clocks)

    timeline_inputs = TimelineInputs(
        evaluation_date=evaluation_date,
        facts_used={name: sorted(clock.relevant_dates.keys()) for name, clock in clocks.items()},
        missing_prerequisites={
            name: clock.missing_prerequisites for name, clock in clocks.items() if clock.missing_prerequisites
        },
    )

    deadlines = _collect_deadlines(clocks)
    timeline_status = TimelineStatus(
        current_phase=_determine_current_phase(facts=facts, clocks=clocks),
        clocks=clocks,
        deadlines=deadlines,
        risk_flags=risk_flags,
        action_items=action_items,
    )

    return {
        "timeline_inputs": timeline_inputs,
        "timeline_status": timeline_status,
    }


def _collect_deadlines(clocks: dict[str, object]) -> list[DeadlineItem]:
    deadlines: list[DeadlineItem] = []
    for clock_name, clock in clocks.items():
        if getattr(clock, "status", None) != "active":
            continue
        for label, value in clock.relevant_dates.items():
            if "deadline" in label or label.endswith("_end"):
                deadlines.append(
                    DeadlineItem(
                        type=clock_name,
                        due_date=value,
                        message=f"{clock_name} deadline on {value}",
                    )
                )
    return deadlines


def _determine_current_phase(*, facts: dict[str, str], clocks: dict[str, object]) -> str:
    if facts.get("category") == "C03C" and clocks["stem_opt_unemployment"].status == "active":
        return "stem_opt_active"
    if clocks["opt_unemployment"].status == "active":
        return "opt_active"
    if clocks["grace_period"].status == "active":
        return "grace_period"
    if clocks["cap_gap"].status == "active":
        return "cap_gap"
    return "unknown"

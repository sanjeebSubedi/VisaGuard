from app.services.timeline.actions import build_risk_flags_and_actions
from app.services.timeline.types import ClockResult


def test_actions_include_deadline_warning_for_approaching_clock():
    clocks = {
        "opt_unemployment": ClockResult(
            status="active",
            relevant_dates={"limit_date": "2026-04-01"},
            days_remaining=5,
            missing_prerequisites=[],
        )
    }

    risk_flags, action_items = build_risk_flags_and_actions(clocks)

    assert any(flag.type == "limit_approaching" for flag in risk_flags)
    assert any(item.type == "review_unemployment_limit" for item in action_items)


def test_actions_include_insufficient_data_flag():
    clocks = {
        "cap_gap": ClockResult(
            status="insufficient_data",
            relevant_dates={},
            missing_prerequisites=["cap_gap_end_date"],
        )
    }

    risk_flags, action_items = build_risk_flags_and_actions(clocks)

    assert any(flag.type == "insufficient_data" for flag in risk_flags)

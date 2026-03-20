from __future__ import annotations

from app.services.timeline.types import ActionItem, ClockResult, RiskFlag


def build_risk_flags_and_actions(
    clocks: dict[str, ClockResult],
) -> tuple[list[RiskFlag], list[ActionItem]]:
    risk_flags: list[RiskFlag] = []
    action_items: list[ActionItem] = []

    for clock_name, clock in clocks.items():
        if clock.status == "insufficient_data":
            risk_flags.append(
                RiskFlag(
                    type="insufficient_data",
                    severity="medium",
                    message=f"Missing prerequisites for {clock_name}",
                    related_clock=clock_name,
                )
            )
            continue

        if clock.status != "active" or clock.days_remaining is None:
            continue

        if clock.days_remaining <= 7:
            is_limit_clock = clock.limit_days is not None or "unemployment" in clock_name
            risk_type = "limit_approaching" if is_limit_clock else "deadline_approaching"
            action_type = "review_unemployment_limit" if is_limit_clock else "review_deadline"
            risk_flags.append(
                RiskFlag(
                    type=risk_type,
                    severity="high",
                    message=f"{clock_name} requires attention within {clock.days_remaining} days",
                    related_clock=clock_name,
                )
            )
            action_items.append(
                ActionItem(
                    type=action_type,
                    priority="high",
                    message=f"Review {clock_name} before its deadline",
                    related_clock=clock_name,
                )
            )

    return risk_flags, action_items

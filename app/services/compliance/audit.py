from __future__ import annotations

from app.services.policy_agent.types import PolicyVerdict
from app.services.timeline.types import TimelineStatus


def build_audit_summary(*, overall_state: str, timeline_status: TimelineStatus | None, policy_verdict: PolicyVerdict | None) -> str:
    parts: list[str] = []

    if timeline_status is not None:
        opt_clock = timeline_status.clocks.get("opt_unemployment")
        if opt_clock and opt_clock.days_remaining is not None:
            parts.append(f"{opt_clock.days_remaining} days remaining on the OPT unemployment clock")
        elif timeline_status.current_phase == "grace_period":
            parts.append("Grace period is currently active")
        elif timeline_status.current_phase == "cap_gap":
            parts.append("Cap-Gap coverage is currently active")
        else:
            parts.append(f"Timeline phase is {timeline_status.current_phase}")

    if policy_verdict is not None:
        if policy_verdict.verdict == "directly_related":
            parts.append("job is directly related to the major")
        elif policy_verdict.verdict == "not_directly_related":
            parts.append("job is not directly related to the major")
        elif policy_verdict.verdict == "unclear":
            parts.append("job relevance remains unclear")
        else:
            parts.append("policy evidence is insufficient")

    parts.append(f"final state is {overall_state}")
    return "; ".join(parts) + "."

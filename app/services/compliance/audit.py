from __future__ import annotations

from app.services.policy_agent.types import PolicyVerdict
from app.services.timeline.types import TimelineStatus


def build_audit_summary(*, overall_state: str, timeline_status: TimelineStatus | None, policy_verdict: PolicyVerdict | None) -> str:
    timeline_sentence = _build_timeline_sentence(timeline_status, overall_state)
    policy_sentence = _build_policy_sentence(policy_verdict)

    if timeline_sentence and policy_sentence:
        return f"{policy_sentence}, and {timeline_sentence}."
    if policy_sentence:
        return policy_sentence + "."
    if timeline_sentence:
        return timeline_sentence + "."
    return f"Your current compliance result is {overall_state.replace('_', ' ').title()}."


def build_confidence_points(*, timeline_status: TimelineStatus | None, policy_verdict: PolicyVerdict | None) -> list[str]:
    points: list[str] = []

    if timeline_status is not None:
        opt_clock = timeline_status.clocks.get("opt_unemployment")
        if opt_clock and opt_clock.days_remaining is not None:
            points.append(f"{opt_clock.days_remaining} days remaining on OPT")
        elif timeline_status.current_phase == "grace_period":
            points.append("Grace period is currently active")
        elif timeline_status.current_phase == "cap_gap":
            points.append("Cap-Gap coverage is currently active")

    if policy_verdict is not None:
        if policy_verdict.verdict == "directly_related":
            points.append("Job directly relates to your major")
        elif policy_verdict.verdict == "not_directly_related":
            points.append("Job does not directly relate to your major")
        elif policy_verdict.verdict == "unclear":
            points.append("Job relevance still needs review")
        else:
            points.append("Policy evidence is still being confirmed")

    return points[:3]


def _build_timeline_sentence(timeline_status: TimelineStatus | None, overall_state: str) -> str | None:
    if timeline_status is None:
        return None

    opt_clock = timeline_status.clocks.get("opt_unemployment")
    if opt_clock and opt_clock.days_remaining is not None:
        if overall_state == "IN_STATUS":
            return "your timeline is well within the standard OPT limits"
        return f"you have {opt_clock.days_remaining} days remaining on your OPT unemployment clock"

    if timeline_status.current_phase == "grace_period":
        return "you are currently within your grace period"
    if timeline_status.current_phase == "cap_gap":
        return "your Cap-Gap coverage is currently active"
    return None


def _build_policy_sentence(policy_verdict: PolicyVerdict | None) -> str | None:
    if policy_verdict is None:
        return None

    if policy_verdict.verdict == "directly_related":
        return "Your job is directly related to your major"
    if policy_verdict.verdict == "not_directly_related":
        return "Your current job does not appear to be directly related to your major"
    if policy_verdict.verdict == "unclear":
        return "Your job duties still need review to confirm that they match your major"
    return "Your policy evidence is still being reviewed"

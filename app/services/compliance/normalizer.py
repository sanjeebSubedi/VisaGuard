from __future__ import annotations

from app.services.compliance.types import ComplianceEvaluation
from app.services.policy_agent.types import PolicyVerdict
from app.services.timeline.types import ClockResult, TimelineStatus


def normalize_upstream_signals(*, timeline_status: TimelineStatus | None, policy_verdict: PolicyVerdict | None) -> ComplianceEvaluation:
    timeline_unknown = _timeline_unknown(timeline_status)
    timeline_grace_period_active = bool(timeline_status and timeline_status.current_phase == "grace_period")
    timeline_cap_gap_active = bool(timeline_status and timeline_status.current_phase == "cap_gap")
    timeline_violation = _timeline_violation(timeline_status)
    timeline_warning_active = bool(timeline_status and timeline_status.risk_flags)
    timeline_passes = bool(
        timeline_status
        and not timeline_unknown
        and not timeline_violation
    )

    policy_passes = bool(policy_verdict and policy_verdict.verdict == "directly_related")
    policy_fails = bool(policy_verdict and policy_verdict.verdict == "not_directly_related")
    policy_unclear = bool(policy_verdict and policy_verdict.verdict == "unclear")
    policy_unknown = bool(
        policy_verdict is None
        or policy_verdict.verdict == "insufficient_policy_evidence"
    )

    return ComplianceEvaluation(
        timeline_passes=timeline_passes,
        timeline_violation=timeline_violation,
        timeline_warning_active=timeline_warning_active,
        timeline_grace_period_active=timeline_grace_period_active,
        timeline_cap_gap_active=timeline_cap_gap_active,
        timeline_unknown=timeline_unknown,
        policy_passes=policy_passes,
        policy_fails=policy_fails,
        policy_unclear=policy_unclear,
        policy_unknown=policy_unknown,
    )


def _timeline_unknown(timeline_status: TimelineStatus | None) -> bool:
    if timeline_status is None:
        return True
    if timeline_status.current_phase == "unknown":
        return True
    return any(clock.status == "insufficient_data" for clock in timeline_status.clocks.values())


def _timeline_violation(timeline_status: TimelineStatus | None) -> bool:
    if timeline_status is None:
        return False
    if timeline_status.current_phase == "out_of_status":
        return True
    return any(_clock_limit_exhausted(clock) for clock in timeline_status.clocks.values())


def _clock_limit_exhausted(clock: ClockResult) -> bool:
    return clock.status == "active" and clock.limit_days is not None and clock.days_remaining is not None and clock.days_remaining <= 0

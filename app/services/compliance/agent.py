from __future__ import annotations

from app.services.compliance.actions import compose_action_plan
from app.services.compliance.audit import build_audit_summary, build_confidence_points
from app.services.compliance.decision_matrix import determine_overall_state
from app.services.compliance.normalizer import normalize_upstream_signals
from app.services.compliance.severity import determine_severity
from app.services.compliance.types import FinalComplianceRecord
from app.services.policy_agent.types import PolicyVerdict
from app.services.timeline.types import TimelineStatus


def evaluate_compliance_state(state: dict[str, object]) -> dict[str, object]:
    timeline_status = _validate_timeline_status(state.get("timeline_status"))
    policy_verdict = _validate_policy_verdict(state.get("policy_verdict"))

    evaluation = normalize_upstream_signals(
        timeline_status=timeline_status,
        policy_verdict=policy_verdict,
    )
    overall_state = determine_overall_state(evaluation)
    severity = determine_severity(overall_state=overall_state, evaluation=evaluation)
    action_plan = compose_action_plan(
        overall_state=overall_state,
        evaluation=evaluation,
        timeline_status=timeline_status,
    )
    audit_summary = build_audit_summary(
        overall_state=overall_state,
        timeline_status=timeline_status,
        policy_verdict=policy_verdict,
    )
    confidence_points = build_confidence_points(
        timeline_status=timeline_status,
        policy_verdict=policy_verdict,
    )

    record = FinalComplianceRecord(
        overall_state=overall_state,
        severity=severity,
        action_plan=action_plan,
        audit_summary=audit_summary,
        confidence_points=confidence_points,
    )

    updated_state = dict(state)
    updated_state["final_compliance_record"] = record.model_dump()
    return updated_state


def _validate_timeline_status(value: object) -> TimelineStatus | None:
    if value is None:
        return None
    if isinstance(value, TimelineStatus):
        return value
    return TimelineStatus.model_validate(value)


def _validate_policy_verdict(value: object) -> PolicyVerdict | None:
    if value is None:
        return None
    if isinstance(value, PolicyVerdict):
        return value
    return PolicyVerdict.model_validate(value)

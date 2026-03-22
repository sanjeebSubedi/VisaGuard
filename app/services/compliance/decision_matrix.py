from __future__ import annotations

from app.services.compliance.types import ComplianceEvaluation


def determine_overall_state(evaluation: ComplianceEvaluation) -> str:
    if evaluation.timeline_violation:
        return "OUT_OF_STATUS"
    if evaluation.policy_fails:
        return "OUT_OF_STATUS"
    if evaluation.timeline_grace_period_active:
        return "GRACE_PERIOD"
    if evaluation.timeline_cap_gap_active:
        return "CAP_GAP"
    if evaluation.timeline_unknown or evaluation.policy_unknown:
        return "UNKNOWN"
    if evaluation.timeline_passes and evaluation.policy_passes:
        return "IN_STATUS"
    if evaluation.policy_unclear:
        return "UNKNOWN"
    return "UNKNOWN"

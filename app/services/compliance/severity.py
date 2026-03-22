from __future__ import annotations

from app.services.compliance.types import ComplianceEvaluation


def determine_severity(*, overall_state: str, evaluation: ComplianceEvaluation) -> str:
    if overall_state == "OUT_OF_STATUS":
        return "VIOLATION"
    if overall_state in {"GRACE_PERIOD", "CAP_GAP"} and evaluation.timeline_warning_active:
        return "CRITICAL"
    if overall_state == "UNKNOWN":
        return "WARNING"
    if evaluation.timeline_warning_active or evaluation.policy_unclear:
        return "WARNING"
    return "INFO"

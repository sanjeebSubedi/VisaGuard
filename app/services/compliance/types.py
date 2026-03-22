from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComplianceEvaluation(BaseModel):
    timeline_passes: bool
    timeline_violation: bool
    timeline_warning_active: bool
    timeline_grace_period_active: bool
    timeline_cap_gap_active: bool
    timeline_unknown: bool
    policy_passes: bool
    policy_fails: bool
    policy_unclear: bool
    policy_unknown: bool


class FinalComplianceRecord(BaseModel):
    overall_state: Literal["IN_STATUS", "OUT_OF_STATUS", "GRACE_PERIOD", "CAP_GAP", "UNKNOWN"]
    severity: Literal["INFO", "WARNING", "CRITICAL", "VIOLATION"]
    action_plan: list[str] = Field(default_factory=list)
    audit_summary: str

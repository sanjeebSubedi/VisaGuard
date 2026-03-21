from __future__ import annotations

from typing import NotRequired, TypedDict


class VisaGuardState(TypedDict, total=False):
    cip_code: str
    original_document_paths: list[str]
    timeline_inputs: dict
    timeline_status: dict
    policy_analysis: NotRequired[dict]
    policy_verdict: NotRequired[dict]
    compliance_state: NotRequired[dict]
    action_plans: NotRequired[list[dict]]

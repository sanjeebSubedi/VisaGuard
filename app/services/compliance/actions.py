from __future__ import annotations

from app.services.compliance.types import ComplianceEvaluation
from app.services.timeline.types import TimelineStatus


def compose_action_plan(*, overall_state: str, evaluation: ComplianceEvaluation, timeline_status: TimelineStatus | None) -> list[str]:
    actions: list[str] = []

    if overall_state == "OUT_OF_STATUS":
        actions.append("Contact DSO immediately regarding status violation.")
    elif evaluation.policy_fails or evaluation.policy_unclear:
        actions.append("Contact DSO immediately regarding job duties.")
    elif evaluation.policy_unknown:
        actions.append("Resolve missing policy evidence before relying on employment.")

    if evaluation.timeline_unknown:
        actions.append("Resolve missing timeline evidence before relying on compliance status.")

    if timeline_status is not None:
        for item in timeline_status.action_items:
            if item.message not in actions:
                actions.append(item.message)

    return actions

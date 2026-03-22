from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WorkflowResult


@dataclass(slots=True)
class WorkflowResultPayload:
    user_id: str
    evaluation_date: str
    timeline_status: dict
    policy_analysis: dict
    policy_verdict: dict
    final_compliance_record: dict


def upsert_workflow_result(session: Session, payload: WorkflowResultPayload) -> WorkflowResult:
    existing = session.scalar(
        select(WorkflowResult).where(WorkflowResult.user_id == payload.user_id)
    )
    if existing is None:
        existing = WorkflowResult(
            user_id=payload.user_id,
            evaluation_date=payload.evaluation_date,
            timeline_status=payload.timeline_status,
            policy_analysis=payload.policy_analysis,
            policy_verdict=payload.policy_verdict,
            final_compliance_record=payload.final_compliance_record,
        )
        session.add(existing)
    else:
        existing.evaluation_date = payload.evaluation_date
        existing.timeline_status = payload.timeline_status
        existing.policy_analysis = payload.policy_analysis
        existing.policy_verdict = payload.policy_verdict
        existing.final_compliance_record = payload.final_compliance_record

    session.commit()
    session.refresh(existing)
    return existing

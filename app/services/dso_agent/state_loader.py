from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.models import WorkflowResult


class StudentStateNotFound(RuntimeError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f'No workflow result found for user_id={user_id}. Run the compliance workflow first.')
        self.user_id = user_id


class LoadedStudentState(BaseModel):
    user_id: str
    school_name: str | None = None
    timeline_status: dict
    policy_verdict: dict
    final_compliance_record: dict


def load_student_state(session: Session, user_id: str) -> LoadedStudentState:
    row = session.scalar(
        select(WorkflowResult)
        .where(WorkflowResult.user_id == user_id)
        .order_by(WorkflowResult.updated_at.desc())
    )
    if row is None:
        raise StudentStateNotFound(user_id)
    school_name = None
    if isinstance(row.policy_analysis, dict):
        school_name = row.policy_analysis.get('school_name')
    return LoadedStudentState(
        user_id=row.user_id,
        school_name=school_name,
        timeline_status=row.timeline_status,
        policy_verdict=row.policy_verdict,
        final_compliance_record=row.final_compliance_record,
    )

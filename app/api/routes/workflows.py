from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.workflows import WorkflowResultResponse, WorkflowRunRequest
from app.core.config import Settings
from app.db.models import StudentStateSnapshot, WorkflowResult
from app.db.session import get_db_session
from app.graph.adapter import build_workflow_state
from app.graph.checkpointer import build_checkpointer
from app.graph.nodes import run_compliance_node, run_policy_node, run_timeline_node
from app.graph.workflow import build_compliance_workflow
from app.services.policy_agent.agent import PolicyAgent
from app.services.reasoning_llm import GeminiReasoningClient
from app.services.workflow_results import WorkflowResultPayload, upsert_workflow_result

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("/compliance/users/{user_id}/latest", response_model=WorkflowResultResponse)
def get_latest_workflow_result(
    user_id: str,
    session: Session = Depends(get_db_session),
) -> WorkflowResult:
    result = session.scalar(
        select(WorkflowResult).where(WorkflowResult.user_id == user_id)
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Workflow result not found")
    return result


@router.post("/compliance/run")
def run_compliance_workflow(
    payload: WorkflowRunRequest = Body(...),
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    return run_workflow_for_user(
        session=session,
        user_id=payload.user_id,
        evaluation_date=payload.evaluation_date,
    )


def run_workflow_for_user(*, session: Session, user_id: str, evaluation_date: str | None) -> dict[str, object]:
    snapshot = session.scalar(
        select(StudentStateSnapshot)
        .where(StudentStateSnapshot.user_id == user_id)
        .order_by(StudentStateSnapshot.version.desc())
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    resolved_evaluation_date = evaluation_date or date.today().isoformat()
    state = build_workflow_state(snapshot=snapshot, evaluation_date=resolved_evaluation_date)
    settings = Settings()
    if not Path(settings.policy_index_path).exists():
        raise HTTPException(status_code=500, detail="Policy index is missing")
    policy_root = Path(settings.policy_data_root)
    reasoning_client = GeminiReasoningClient(api_key=settings.gemini_api_key)
    policy_agent = PolicyAgent(
        index_path=Path(settings.policy_index_path),
        cip_dataset_path=policy_root / "cip_codes.json",
        reasoning_client=reasoning_client,
        model_name=settings.gemini_model,
    )

    with build_checkpointer(settings) as checkpointer:
        workflow = build_compliance_workflow(
            timeline_node=run_timeline_node,
            policy_node=lambda current_state: run_policy_node(current_state, policy_agent),
            compliance_node=run_compliance_node,
            checkpointer=checkpointer,
        )
        result = workflow.invoke(
            state,
            config={"configurable": {"thread_id": user_id}},
        )

    upsert_workflow_result(
        session,
        WorkflowResultPayload(
            user_id=user_id,
            evaluation_date=resolved_evaluation_date,
            timeline_status=result["timeline_status"],
            policy_analysis=result["policy_analysis"],
            policy_verdict=result["policy_verdict"],
            final_compliance_record=result["final_compliance_record"],
        ),
    )
    return result

from sqlalchemy import select

from app.services.workflow_results import WorkflowResultPayload, upsert_workflow_result


def test_upsert_workflow_result_replaces_latest_result(db_session):
    upsert_workflow_result(
        db_session,
        WorkflowResultPayload(
            user_id="student-1",
            evaluation_date="2026-03-22",
            timeline_status={"current_phase": "opt_active"},
            policy_analysis={"summary": "first"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS"},
        ),
    )
    upsert_workflow_result(
        db_session,
        WorkflowResultPayload(
            user_id="student-1",
            evaluation_date="2026-03-23",
            timeline_status={"current_phase": "grace_period"},
            policy_analysis={"summary": "second"},
            policy_verdict={"verdict": "unclear"},
            final_compliance_record={"overall_state": "UNKNOWN"},
        ),
    )

    row = db_session.scalar(select_from_latest_result())

    assert row is not None
    assert row.evaluation_date == "2026-03-23"
    assert row.timeline_status["current_phase"] == "grace_period"
    assert row.final_compliance_record["overall_state"] == "UNKNOWN"


def select_from_latest_result():
    from app.db.models import WorkflowResult

    return select(WorkflowResult).where(WorkflowResult.user_id == "student-1")


from app.db.models import WorkflowResult
from app.services.dso_agent.state_loader import LoadedStudentState, load_student_state


def test_loaded_state_exposes_latest_workflow_fields():
    payload = LoadedStudentState.model_validate(
        {
            "user_id": "user0",
            "school_name": "New York University",
            "timeline_status": {"current_phase": "opt_active", "clocks": {}},
            "policy_verdict": {"verdict": "directly_related"},
            "final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"},
        }
    )
    assert payload.final_compliance_record["overall_state"] == "IN_STATUS"


def test_load_student_state_reads_current_workflow_row_for_user(db_session):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-21",
            timeline_status={"current_phase": "opt_active"},
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO"},
        )
    )
    db_session.commit()

    loaded = load_student_state(db_session, "user0")

    assert loaded.timeline_status["current_phase"] == "opt_active"
    assert loaded.school_name == "New York University"

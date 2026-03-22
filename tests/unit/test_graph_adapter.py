from app.db.models import StudentStateSnapshot
from app.graph.adapter import build_workflow_state


def test_build_workflow_state_keeps_extracted_data_nested():
    snapshot = StudentStateSnapshot(
        user_id="student-1",
        version=3,
        snapshot_payload={
            "cip_code": "11.0701",
            "major": "Computer Science",
            "position_title": "Software Engineer",
        },
    )

    state = build_workflow_state(snapshot=snapshot, evaluation_date="2026-03-22")

    assert state["evaluation_date"] == "2026-03-22"
    assert state["extracted_data"]["cip_code"] == "11.0701"
    assert state["extracted_data"]["position_title"] == "Software Engineer"


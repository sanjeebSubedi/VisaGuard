from contextlib import nullcontext

from sqlalchemy import select

from app.api.routes import workflows as workflow_routes
from app.db.models import StudentStateSnapshot, WorkflowResult


def test_workflow_run_endpoint_loads_snapshot_and_returns_full_state(client, db_session, monkeypatch):
    snapshot = StudentStateSnapshot(
        user_id="student-1",
        version=1,
        snapshot_payload={
            "cip_code": "11.0701",
            "major": "Computer Science",
            "position_title": "Software Engineer",
            "job_duties": "Build distributed systems",
        },
        field_eligibility_map={},
        provenance_map={},
    )
    db_session.add(snapshot)
    db_session.commit()

    def fake_run_workflow_for_user(*, session, user_id, evaluation_date):
        assert session is db_session
        assert user_id == "student-1"
        assert evaluation_date == "2026-03-22"
        return {
            "extracted_data": snapshot.snapshot_payload,
            "timeline_status": {"current_phase": "opt_active"},
            "policy_verdict": {"verdict": "directly_related"},
            "final_compliance_record": {"overall_state": "IN_STATUS"},
        }

    monkeypatch.setattr(workflow_routes, "run_workflow_for_user", fake_run_workflow_for_user)

    response = client.post(
        "/api/workflows/compliance/run",
        json={"user_id": "student-1", "evaluation_date": "2026-03-22"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timeline_status"]["current_phase"] == "opt_active"
    assert body["policy_verdict"]["verdict"] == "directly_related"
    assert body["final_compliance_record"]["overall_state"] == "IN_STATUS"


def test_workflow_run_endpoint_returns_404_when_snapshot_missing(client):
    response = client.post(
        "/api/workflows/compliance/run",
        json={"user_id": "missing"},
    )

    assert response.status_code == 404


def test_workflow_run_endpoint_persists_latest_result(client, db_session, monkeypatch, tmp_path):
    snapshot = StudentStateSnapshot(
        user_id="student-1",
        version=1,
        snapshot_payload={
            "cip_code": "11.0701",
            "major": "Computer Science",
            "position_title": "Software Engineer",
            "job_duties": "Build distributed systems",
        },
        field_eligibility_map={},
        provenance_map={},
    )
    db_session.add(snapshot)
    db_session.commit()

    policy_root = tmp_path / "policy"
    policy_root.mkdir()
    (policy_root / "cip_codes.json").write_text("{}")
    index_path = tmp_path / "policy-index.json"
    index_path.write_text("{}")

    monkeypatch.setenv("POLICY_DATA_ROOT", str(policy_root))
    monkeypatch.setenv("POLICY_INDEX_PATH", str(index_path))

    class FakePolicyAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeReasoningClient:
        def __init__(self, api_key):
            self.api_key = api_key

    class FakeWorkflow:
        def invoke(self, state, config):
            assert state["extracted_data"]["cip_code"] == "11.0701"
            assert config["configurable"]["thread_id"] == "student-1"
            return {
                **state,
                "timeline_inputs": {"evaluation_date": "2026-03-22"},
                "timeline_status": {"current_phase": "opt_active"},
                "policy_analysis": {"summary": "Strong match"},
                "policy_verdict": {"verdict": "directly_related"},
                "final_compliance_record": {"overall_state": "IN_STATUS"},
            }

    monkeypatch.setattr(workflow_routes, "PolicyAgent", FakePolicyAgent)
    monkeypatch.setattr(workflow_routes, "GeminiReasoningClient", FakeReasoningClient)
    monkeypatch.setattr(workflow_routes, "build_checkpointer", lambda settings: nullcontext(object()))
    monkeypatch.setattr(workflow_routes, "build_compliance_workflow", lambda **kwargs: FakeWorkflow())

    response = client.post(
        "/api/workflows/compliance/run",
        json={"user_id": "student-1", "evaluation_date": "2026-03-22"},
    )

    assert response.status_code == 200
    row = db_session.scalar(select(WorkflowResult).where(WorkflowResult.user_id == "student-1"))
    assert row is not None
    assert row.evaluation_date == "2026-03-22"
    assert row.timeline_status["current_phase"] == "opt_active"
    assert row.final_compliance_record["overall_state"] == "IN_STATUS"


def test_workflow_run_endpoint_fails_when_policy_index_missing(client, db_session, monkeypatch, tmp_path):
    snapshot = StudentStateSnapshot(
        user_id="student-1",
        version=1,
        snapshot_payload={"cip_code": "11.0701"},
        field_eligibility_map={},
        provenance_map={},
    )
    db_session.add(snapshot)
    db_session.commit()

    policy_root = tmp_path / "policy"
    policy_root.mkdir()
    (policy_root / "cip_codes.json").write_text("{}")

    monkeypatch.setenv("POLICY_DATA_ROOT", str(policy_root))
    monkeypatch.setenv("POLICY_INDEX_PATH", str(tmp_path / "missing-index.json"))

    response = client.post(
        "/api/workflows/compliance/run",
        json={"user_id": "student-1", "evaluation_date": "2026-03-22"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Policy index is missing"

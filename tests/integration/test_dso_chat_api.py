from app.api.routes import dso as dso_routes
from app.db.models import WorkflowResult


class FakeWorkflow:
    def invoke(self, state):
        return {
            **state,
            "answer": "Yes, if each job independently qualifies for OPT.",
            "citations": [],
            "confidence": "high",
            "needs_human_escalation": False,
            "answer_mode": "general_policy",
        }


class FailingWorkflow:
    def invoke(self, state):
        raise dso_routes.DSOUnavailableError("provider unavailable")


class MalformedWorkflow:
    def invoke(self, state):
        raise dso_routes.DSOUnavailableError("malformed output")


def test_dso_chat_returns_404_when_workflow_result_missing(client):
    response = client.post("/api/dso/chat", json={"user_id": "missing", "message": "How many days do I have left?", "chat_history": []})
    assert response.status_code == 404
    assert response.json() == {"detail": "No workflow result found for user_id=missing. Run the compliance workflow first."}


def test_dso_chat_returns_structured_response(client, db_session, monkeypatch):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-22",
            timeline_status={"current_phase": "opt_active", "clocks": {}},
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO", "action_plan": [], "audit_summary": "In status."},
        )
    )
    db_session.commit()
    monkeypatch.setattr(dso_routes, "build_dso_chat_workflow", lambda **kwargs: FakeWorkflow())

    response = client.post("/api/dso/chat", json={"user_id": "user0", "message": "Can I work two jobs on OPT?", "chat_history": []})
    assert response.status_code == 200
    assert "answer" in response.json()


def test_dso_chat_returns_503_when_reasoning_provider_fails(client, db_session, monkeypatch):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-22",
            timeline_status={"current_phase": "opt_active", "clocks": {}},
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO", "action_plan": [], "audit_summary": "In status."},
        )
    )
    db_session.commit()
    monkeypatch.setattr(dso_routes, "build_dso_chat_workflow", lambda **kwargs: FailingWorkflow())

    response = client.post("/api/dso/chat", json={"user_id": "user0", "message": "Can I work two jobs on OPT?", "chat_history": []})
    assert response.status_code == 503
    assert response.json() == {"detail": "DSO agent is temporarily unavailable. Please try again or contact your DSO."}


def test_dso_chat_returns_503_when_gemini_output_is_malformed(client, db_session, monkeypatch):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-22",
            timeline_status={"current_phase": "opt_active", "clocks": {}},
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO", "action_plan": [], "audit_summary": "In status."},
        )
    )
    db_session.commit()
    monkeypatch.setattr(dso_routes, "build_dso_chat_workflow", lambda **kwargs: MalformedWorkflow())

    response = client.post("/api/dso/chat", json={"user_id": "user0", "message": "Can I work two jobs on OPT?", "chat_history": []})
    assert response.status_code == 503
    assert response.json() == {"detail": "DSO agent is temporarily unavailable. Please try again or contact your DSO."}

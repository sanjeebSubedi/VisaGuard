from app.graph.nodes import run_compliance_node, run_policy_node, run_timeline_node


def test_timeline_node_returns_only_timeline_delta(monkeypatch):
    sample_state = {
        "extracted_data": {"cip_code": "11.0701"},
        "evaluation_date": "2026-03-22",
    }

    class FakeModel:
        def __init__(self, payload):
            self._payload = payload

        def model_dump(self):
            return self._payload

    def fake_evaluate_timeline(*, facts, evaluation_date):
        assert facts == sample_state["extracted_data"]
        assert evaluation_date == "2026-03-22"
        return {
            "timeline_inputs": FakeModel({"evaluation_date": evaluation_date}),
            "timeline_status": FakeModel({"current_phase": "opt_active"}),
        }

    monkeypatch.setattr("app.graph.nodes.evaluate_timeline", fake_evaluate_timeline)

    delta = run_timeline_node(sample_state)

    assert delta == {
        "timeline_inputs": {"evaluation_date": "2026-03-22"},
        "timeline_status": {"current_phase": "opt_active"},
    }


def test_policy_node_returns_only_policy_delta(monkeypatch):
    sample_state = {
        "extracted_data": {"cip_code": "11.0701", "job_duties": "Build APIs"},
    }

    def fake_evaluate_policy_state(state, agent):
        assert state == sample_state["extracted_data"]
        assert agent == "policy-agent"
        return {
            "extracted_data": state,
            "policy_analysis": {"summary": "Strong match"},
            "policy_verdict": {"verdict": "directly_related"},
        }

    monkeypatch.setattr("app.graph.nodes.evaluate_policy_state", fake_evaluate_policy_state)

    delta = run_policy_node(sample_state, "policy-agent")

    assert delta == {
        "policy_analysis": {"summary": "Strong match"},
        "policy_verdict": {"verdict": "directly_related"},
    }


def test_compliance_node_returns_only_final_record(monkeypatch):
    sample_state = {
        "timeline_status": {"current_phase": "opt_active"},
        "policy_verdict": {"verdict": "directly_related"},
    }

    def fake_evaluate_compliance_state(state):
        assert state == sample_state
        return {
            **state,
            "final_compliance_record": {
                "overall_state": "IN_STATUS",
                "severity": "INFO",
                "action_plan": [],
                "audit_summary": "Everything is compliant.",
            },
        }

    monkeypatch.setattr("app.graph.nodes.evaluate_compliance_state", fake_evaluate_compliance_state)

    delta = run_compliance_node(sample_state)

    assert delta == {
        "final_compliance_record": {
            "overall_state": "IN_STATUS",
            "severity": "INFO",
            "action_plan": [],
            "audit_summary": "Everything is compliant.",
        }
    }

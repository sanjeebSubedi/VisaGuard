import pytest

from app.graph.workflow import build_compliance_workflow


def test_workflow_runs_timeline_and_policy_before_compliance():
    events: list[str] = []

    def timeline_node(state):
        events.append("timeline")
        assert state["extracted_data"]["cip_code"] == "11.0701"
        return {"timeline_status": {"current_phase": "opt_active"}}

    def policy_node(state):
        events.append("policy")
        assert state["extracted_data"]["major"] == "Computer Science"
        return {"policy_verdict": {"verdict": "directly_related"}}

    def compliance_node(state):
        events.append("compliance")
        assert state["timeline_status"]["current_phase"] == "opt_active"
        assert state["policy_verdict"]["verdict"] == "directly_related"
        return {
            "final_compliance_record": {
                "overall_state": "IN_STATUS",
                "severity": "INFO",
                "action_plan": [],
                "audit_summary": "Everything is compliant.",
            }
        }

    workflow = build_compliance_workflow(
        timeline_node=timeline_node,
        policy_node=policy_node,
        compliance_node=compliance_node,
    )

    result = workflow.invoke(
        {
            "extracted_data": {
                "cip_code": "11.0701",
                "major": "Computer Science",
            },
            "evaluation_date": "2026-03-22",
        },
        config={"configurable": {"thread_id": "student-1"}},
    )

    assert result["timeline_status"]["current_phase"] == "opt_active"
    assert result["policy_verdict"]["verdict"] == "directly_related"
    assert result["final_compliance_record"]["overall_state"] == "IN_STATUS"
    assert events[-1] == "compliance"
    assert set(events[:2]) == {"timeline", "policy"}


def test_workflow_fails_fast_when_policy_node_raises():
    def timeline_node(state):
        return {"timeline_status": {"current_phase": "opt_active"}}

    def policy_node(state):
        raise RuntimeError("policy boom")

    def compliance_node(state):
        raise AssertionError("compliance should not run")

    workflow = build_compliance_workflow(
        timeline_node=timeline_node,
        policy_node=policy_node,
        compliance_node=compliance_node,
    )

    with pytest.raises(RuntimeError, match="policy boom"):
        workflow.invoke(
            {
                "extracted_data": {"cip_code": "11.0701"},
                "evaluation_date": "2026-03-22",
            },
            config={"configurable": {"thread_id": "student-1"}},
        )

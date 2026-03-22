from app.graph.state import VisaGuardState


def test_langgraph_state_supports_timeline_outputs():
    state: VisaGuardState = {
        "cip_code": "11.0701",
        "timeline_inputs": {"evaluation_date": "2026-03-20"},
        "timeline_status": {"current_phase": "opt_active", "clocks": {}},
    }

    assert state["timeline_status"]["current_phase"] == "opt_active"


def test_langgraph_state_module_imports():
    assert VisaGuardState is not None



def test_langgraph_state_supports_policy_outputs():
    state: VisaGuardState = {
        "cip_code": "11.0701",
        "policy_analysis": {"summary": "Job duties align with core computing coursework."},
        "policy_verdict": {"verdict": "directly_related", "confidence": "high"},
    }

    assert state["policy_verdict"]["verdict"] == "directly_related"


def test_langgraph_state_supports_final_compliance_record():
    state: VisaGuardState = {
        "final_compliance_record": {
            "overall_state": "IN_STATUS",
            "severity": "INFO",
            "action_plan": [],
            "audit_summary": "Everything is currently compliant.",
        }
    }

    assert state["final_compliance_record"]["overall_state"] == "IN_STATUS"


def test_langgraph_state_supports_nested_workflow_inputs():
    state: VisaGuardState = {
        "extracted_data": {
            "cip_code": "11.0701",
            "major": "Computer Science",
        },
        "evaluation_date": "2026-03-22",
        "user_profile": {"preferred_name": "Ada"},
    }

    assert state["extracted_data"]["cip_code"] == "11.0701"
    assert state["evaluation_date"] == "2026-03-22"

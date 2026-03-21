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

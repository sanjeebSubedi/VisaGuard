from __future__ import annotations

from app.services.compliance.agent import evaluate_compliance_state
from app.services.policy_agent.agent import evaluate_policy_state
from app.services.timeline.evaluator import evaluate_timeline


def run_timeline_node(state: dict[str, object]) -> dict[str, object]:
    result = evaluate_timeline(
        facts=_extracted_data(state),
        evaluation_date=str(state["evaluation_date"]),
    )
    return {
        "timeline_inputs": result["timeline_inputs"].model_dump(),
        "timeline_status": result["timeline_status"].model_dump(),
    }


def run_policy_node(state: dict[str, object], agent: object) -> dict[str, object]:
    result = evaluate_policy_state(_extracted_data(state), agent)
    return {
        "policy_analysis": result["policy_analysis"].model_dump()
        if hasattr(result["policy_analysis"], "model_dump")
        else result["policy_analysis"],
        "policy_verdict": result["policy_verdict"].model_dump()
        if hasattr(result["policy_verdict"], "model_dump")
        else result["policy_verdict"],
    }


def run_compliance_node(state: dict[str, object]) -> dict[str, object]:
    result = evaluate_compliance_state(state)
    return {
        "final_compliance_record": result["final_compliance_record"],
    }


def _extracted_data(state: dict[str, object]) -> dict[str, str]:
    data = state.get("extracted_data", {})
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if isinstance(value, str)}

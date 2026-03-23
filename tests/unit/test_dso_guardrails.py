from app.services.dso_agent.guardrails import apply_guardrails
from app.services.dso_agent.types import DSOResponse


def _response(answer_mode: str = "personalized_status", answer: str = "Base answer") -> DSOResponse:
    return DSOResponse(
        answer=answer,
        citations=[],
        confidence="medium",
        needs_human_escalation=False,
        answer_mode=answer_mode,
    )


def test_guardrails_append_hardcoded_escalation_for_violation_state():
    response = apply_guardrails(
        response=_response(answer_mode="escalation_sensitive"),
        student_state={"final_compliance_record": {"overall_state": "OUT_OF_STATUS", "severity": "VIOLATION"}},
        question="What should I do now?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()


def test_guardrails_append_escalation_for_critical_severity():
    response = apply_guardrails(
        response=_response(),
        student_state={"final_compliance_record": {"overall_state": "UNKNOWN", "severity": "CRITICAL"}},
        question="What should I do now?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()


def test_guardrails_append_escalation_when_router_marks_turn_sensitive():
    response = apply_guardrails(
        response=_response(answer_mode="escalation_sensitive"),
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}},
        question="Am I allowed to keep working if I think I already exceeded my unemployment limit?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()


def test_guardrails_append_escalation_for_cautious_fallback_on_travel_risk():
    response = apply_guardrails(
        response=_response(answer_mode="cautious_fallback"),
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "WARNING"}},
        question="Can I travel to Mexico next week if my status is complicated?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()


def test_guardrails_append_escalation_for_reporting_delay_question():
    response = apply_guardrails(
        response=_response(answer_mode="escalation_sensitive"),
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "WARNING"}},
        question="Can I ignore this reporting deadline for another week?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()


def test_guardrails_append_escalation_for_unauthorized_employment_variant():
    response = apply_guardrails(
        response=_response(answer_mode="cautious_fallback"),
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "WARNING"}},
        question="Can I keep working this side job even if it may not count for OPT?",
    )
    assert "please contact your dso or a qualified immigration attorney" in response.answer.lower()

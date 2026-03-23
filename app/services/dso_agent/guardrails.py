from __future__ import annotations

from app.services.dso_agent.types import DSOResponse

HARDCODED_ESCALATION = (
    'Because this may have serious immigration consequences, please contact your DSO '
    'or a qualified immigration attorney before acting on this answer.'
)

_STATUS_RISK_TERMS = (
    'out of status',
    'unemployment limit',
    'unauthorized employment',
    'travel',
    'reporting deadline',
    'ignore this reporting deadline',
    'side job',
)


def requires_escalation(*, response: DSOResponse, student_state: dict, question: str) -> bool:
    compliance = student_state.get('final_compliance_record', {}) if isinstance(student_state, dict) else {}
    overall_state = compliance.get('overall_state')
    severity = compliance.get('severity')
    if overall_state == 'OUT_OF_STATUS':
        return True
    if severity in {'CRITICAL', 'VIOLATION'}:
        return True
    if response.answer_mode == 'escalation_sensitive':
        return True
    lowered = question.lower()
    if response.answer_mode == 'cautious_fallback' and any(term in lowered for term in _STATUS_RISK_TERMS):
        return True
    return False


def apply_guardrails(*, response: DSOResponse, student_state: dict, question: str) -> DSOResponse:
    if requires_escalation(response=response, student_state=student_state, question=question):
        if HARDCODED_ESCALATION not in response.answer:
            response.answer = f'{response.answer}\n\n{HARDCODED_ESCALATION}'.strip()
        response.needs_human_escalation = True
    return response

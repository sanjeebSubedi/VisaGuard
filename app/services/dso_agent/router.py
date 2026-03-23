from __future__ import annotations


def route_intent(message: str) -> str:
    lowered = message.lower()
    if 'out of status' in lowered or 'exceeded my unemployment limit' in lowered:
        return 'escalation_sensitive'
    if 'travel signature' in lowered or 'how do i' in lowered:
        return 'school_procedure'
    if 'can i' in lowered:
        return 'general_policy'
    return 'personalized_status'

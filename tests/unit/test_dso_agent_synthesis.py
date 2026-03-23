import pytest

from app.services.dso_agent.agent import DSOResponsePayload, synthesize_answer


class FakeReasoningClient:
    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def generate_structured(self, *, model: str, prompt: str, schema):
        self.prompts.append(prompt)
        return self.payload


def test_synthesize_answer_returns_structured_response_from_grounded_inputs():
    response = synthesize_answer(
        message="Can I work two jobs on OPT?",
        mode="general_policy",
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}},
        retrieved_sources=[{"title": "Employment", "citation": "8 CFR", "source_type": "federal", "excerpt": "Employment must be related.", "score": 0.9}],
        reasoning_client=FakeReasoningClient({
            "answer": "Yes, if each job independently qualifies for OPT.",
            "citations": [{"title": "Employment", "citation": "8 CFR", "source_type": "federal", "excerpt": "Employment must be related.", "score": 0.9}],
            "confidence": "high",
            "needs_human_escalation": False,
            "answer_mode": "general_policy",
        }),
        model_name="gemini-test",
    )
    assert response.answer
    assert response.citations


def test_synthesize_answer_uses_precomputed_timeline_fields_instead_of_deriving_math():
    response = synthesize_answer(
        message="How many unemployment days do I have left?",
        mode="personalized_status",
        student_state={
            "timeline_status": {"clocks": {"opt_unemployment": {"status": "active", "days_remaining": 52, "limit_days": 90, "relevant_dates": {"card_start_date": "2026-01-01"}}}},
            "final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"},
        },
        retrieved_sources=[],
        reasoning_client=FakeReasoningClient({
            "answer": "You have 52 days remaining on your OPT unemployment clock.",
            "citations": [],
            "confidence": "high",
            "needs_human_escalation": False,
            "answer_mode": "personalized_status",
        }),
        model_name="gemini-test",
    )
    assert "52" in response.answer


def test_synthesize_answer_refuses_to_derive_missing_time_math():
    response = synthesize_answer(
        message="How many unemployment days do I have left?",
        mode="personalized_status",
        student_state={
            "timeline_status": {"clocks": {"opt_unemployment": {"status": "active", "days_remaining": None, "limit_days": 90, "relevant_dates": {}}}},
            "final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"},
        },
        retrieved_sources=[],
        reasoning_client=FakeReasoningClient({}),
        model_name="gemini-test",
    )
    assert "rerun the workflow or contact your dso" in response.answer.lower()


def test_synthesize_answer_returns_cautious_fallback_when_grounding_is_weak():
    response = synthesize_answer(
        message="How do I get a travel signature?",
        mode="school_procedure",
        student_state={"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}},
        retrieved_sources=[],
        reasoning_client=FakeReasoningClient({}),
        model_name="gemini-test",
    )
    assert response.answer_mode == "cautious_fallback"


def test_synthesize_answer_falls_back_to_federal_guidance_when_school_is_unsupported():
    response = synthesize_answer(
        message="How do I get a travel signature?",
        mode="school_procedure",
        student_state={"school_name": "Unsupported School", "final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}},
        retrieved_sources=[{"title": "Travel", "citation": "8 CFR", "source_type": "federal", "excerpt": "Students may need a travel signature.", "score": 0.8}],
        reasoning_client=FakeReasoningClient({
            "answer": "Federal guidance suggests you may need a travel signature.",
            "citations": [{"title": "Travel", "citation": "8 CFR", "source_type": "federal", "excerpt": "Students may need a travel signature.", "score": 0.8}],
            "confidence": "medium",
            "needs_human_escalation": False,
            "answer_mode": "school_procedure",
        }),
        model_name="gemini-test",
        school_supported=False,
    )
    assert "school-specific procedure guidance is unavailable" in response.answer.lower()


def test_synthesize_answer_uses_federal_guidance_when_supported_school_has_no_local_match():
    response = synthesize_answer(
        message="How do I get a travel signature?",
        mode="school_procedure",
        student_state={"school_name": "New York University", "final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}},
        retrieved_sources=[{"title": "Travel", "citation": "8 CFR", "source_type": "federal", "excerpt": "Students may need a travel signature.", "score": 0.8}],
        reasoning_client=FakeReasoningClient({
            "answer": "Federal guidance suggests you may need a travel signature.",
            "citations": [{"title": "Travel", "citation": "8 CFR", "source_type": "federal", "excerpt": "Students may need a travel signature.", "score": 0.8}],
            "confidence": "medium",
            "needs_human_escalation": False,
            "answer_mode": "school_procedure",
        }),
        model_name="gemini-test",
        school_supported=True,
        university_match_found=False,
    )
    assert "school-specific steps may differ" in response.answer.lower()


def test_dso_response_payload_rejects_noncanonical_enum_values():
    with pytest.raises(Exception):
        DSOResponsePayload.model_validate(
            {
                "answer": "Yes.",
                "citations": [],
                "confidence": "High",
                "needs_human_escalation": False,
                "answer_mode": "General Policy",
            }
        )

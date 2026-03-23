from app.services.dso_agent.types import ChatTurn, DSOCitation, DSOResponse


def test_dso_response_supports_typed_fields():
    response = DSOResponse(
        answer="You are currently in status.",
        citations=[
            DSOCitation(
                title="OPT Reporting",
                citation="8 CFR 214.2(f)",
                source_type="federal",
                excerpt="Students must report...",
                score=0.91,
            )
        ],
        confidence="high",
        needs_human_escalation=False,
        answer_mode="personalized_status",
    )
    assert response.answer_mode == "personalized_status"
    assert response.citations[0].source_type == "federal"
    assert ChatTurn(role="user", content="Hello").role == "user"

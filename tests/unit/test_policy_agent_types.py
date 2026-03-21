from app.services.policy_agent.types import PolicyAnalysis, PolicyRationale, PolicyVerdict, RetrievedSource


def test_policy_verdict_supports_structured_rationale_and_sources():
    verdict = PolicyVerdict(
        verdict="directly_related",
        confidence="high",
        rationale=PolicyRationale(
            major_match="The role aligns with core computer science training.",
            duty_match="The duties involve backend software engineering and distributed systems.",
            policy_basis="The work applies knowledge normally obtained in the degree program.",
            summary="The position is directly related to the student's major.",
        ),
        cited_sources=[
            RetrievedSource(
                source_id="sevp-1004-03-1",
                title="SEVP Policy 1004-03",
                citation="SEVP Policy 1004-03",
                source_type="policy",
                text="Employment must be directly related to the student's major area of study.",
                score=0.98,
            )
        ],
    )

    analysis = PolicyAnalysis(
        cip_code="11.0701",
        cip_title="Computer Science",
        summary="The duties map closely to software engineering responsibilities.",
        evidence_strength="strong",
        retrieved_sources=verdict.cited_sources,
        ambiguity_notes=[],
    )

    assert verdict.rationale.summary == "The position is directly related to the student's major."
    assert analysis.cip_title == "Computer Science"

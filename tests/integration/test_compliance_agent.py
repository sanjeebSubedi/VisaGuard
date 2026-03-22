from app.services.compliance.agent import evaluate_compliance_state
from app.services.policy_agent.types import PolicyRationale, PolicyVerdict
from app.services.timeline.types import ActionItem, ClockResult, TimelineStatus


def test_compliance_agent_writes_final_compliance_record_into_state():
    timeline_status = TimelineStatus(
        current_phase="opt_active",
        clocks={
            "opt_unemployment": ClockResult(
                status="active",
                relevant_dates={"card_start_date": "2026-01-01"},
                days_remaining=5,
                limit_days=90,
            )
        },
        deadlines=[],
        risk_flags=[],
        action_items=[
            ActionItem(
                type="review_unemployment_limit",
                priority="high",
                message="Report employer to SEVP by 2026-06-25",
            )
        ],
    )
    policy_verdict = PolicyVerdict(
        verdict="directly_related",
        confidence="high",
        rationale=PolicyRationale(
            major_match="strong match",
            duty_match="strong match",
            policy_basis="The work applies knowledge gained in the degree program.",
            summary="The role is directly related to the major.",
        ),
        cited_sources=[],
    )

    state = evaluate_compliance_state(
        {
            "timeline_status": timeline_status.model_dump(),
            "policy_verdict": policy_verdict.model_dump(),
        }
    )

    assert state["final_compliance_record"]["overall_state"] == "IN_STATUS"
    assert state["final_compliance_record"]["severity"] == "WARNING"
    assert "Report employer to SEVP by 2026-06-25" in state["final_compliance_record"]["action_plan"]

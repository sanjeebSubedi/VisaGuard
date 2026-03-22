from app.services.compliance.audit import build_audit_summary
from app.services.policy_agent.types import PolicyRationale, PolicyVerdict
from app.services.timeline.types import ClockResult, TimelineStatus


def test_build_audit_summary_combines_timeline_and_policy_basis():
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
        action_items=[],
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

    summary = build_audit_summary(
        overall_state="IN_STATUS",
        timeline_status=timeline_status,
        policy_verdict=policy_verdict,
    )

    assert "5 days remaining" in summary
    assert "directly related" in summary

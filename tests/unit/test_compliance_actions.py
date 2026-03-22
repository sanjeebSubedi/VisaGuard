from app.services.compliance.actions import compose_action_plan
from app.services.compliance.types import ComplianceEvaluation
from app.services.timeline.types import ActionItem, TimelineStatus


def test_compose_action_plan_reuses_timeline_actions_and_adds_policy_followup():
    evaluation = ComplianceEvaluation(
        timeline_passes=True,
        timeline_violation=False,
        timeline_warning_active=True,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=False,
        policy_fails=False,
        policy_unclear=True,
        policy_unknown=False,
    )
    timeline_status = TimelineStatus(
        current_phase="opt_active",
        clocks={},
        deadlines=[],
        risk_flags=[],
        action_items=[
            ActionItem(
                type="review_deadline",
                priority="high",
                message="Report employer to SEVP by 2026-06-25",
            )
        ],
    )

    action_plan = compose_action_plan(
        overall_state="UNKNOWN",
        evaluation=evaluation,
        timeline_status=timeline_status,
    )

    assert action_plan[0] == "Contact DSO immediately regarding job duties."
    assert "Report employer to SEVP by 2026-06-25" in action_plan

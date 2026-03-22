from app.services.compliance.normalizer import normalize_upstream_signals
from app.services.timeline.types import ActionItem, ClockResult, RiskFlag, TimelineStatus
from app.services.policy_agent.types import PolicyRationale, PolicyVerdict


def test_normalize_upstream_signals_maps_warning_timeline_and_policy_pass():
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
        risk_flags=[
            RiskFlag(
                type="limit_approaching",
                severity="high",
                message="opt_unemployment requires attention within 5 days",
                related_clock="opt_unemployment",
            )
        ],
        action_items=[
            ActionItem(
                type="review_unemployment_limit",
                priority="high",
                message="Review opt_unemployment before its deadline",
                related_clock="opt_unemployment",
            )
        ],
    )
    policy_verdict = PolicyVerdict(
        verdict="directly_related",
        confidence="high",
        rationale=PolicyRationale(
            major_match="match",
            duty_match="match",
            policy_basis="basis",
            summary="summary",
        ),
        cited_sources=[],
    )

    evaluation = normalize_upstream_signals(timeline_status=timeline_status, policy_verdict=policy_verdict)

    assert evaluation.timeline_passes is True
    assert evaluation.timeline_warning_active is True
    assert evaluation.policy_passes is True


def test_normalize_upstream_signals_maps_unknown_when_evidence_is_incomplete():
    timeline_status = TimelineStatus(
        current_phase="unknown",
        clocks={
            "opt_unemployment": ClockResult(
                status="insufficient_data",
                missing_prerequisites=["card_start_date"],
            )
        },
        deadlines=[],
        risk_flags=[],
        action_items=[],
    )
    policy_verdict = PolicyVerdict(
        verdict="insufficient_policy_evidence",
        confidence="low",
        rationale=PolicyRationale(
            major_match="missing",
            duty_match="missing",
            policy_basis="missing",
            summary="missing",
        ),
        cited_sources=[],
    )

    evaluation = normalize_upstream_signals(timeline_status=timeline_status, policy_verdict=policy_verdict)

    assert evaluation.timeline_unknown is True
    assert evaluation.policy_unknown is True

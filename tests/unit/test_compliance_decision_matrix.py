from app.services.compliance.decision_matrix import determine_overall_state
from app.services.compliance.types import ComplianceEvaluation


def test_decision_matrix_timeline_violation_dominates_policy_pass():
    evaluation = ComplianceEvaluation(
        timeline_passes=False,
        timeline_violation=True,
        timeline_warning_active=False,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=True,
        policy_fails=False,
        policy_unclear=False,
        policy_unknown=False,
    )

    assert determine_overall_state(evaluation) == "OUT_OF_STATUS"


def test_decision_matrix_policy_failure_makes_student_out_of_status():
    evaluation = ComplianceEvaluation(
        timeline_passes=True,
        timeline_violation=False,
        timeline_warning_active=False,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=False,
        policy_fails=True,
        policy_unclear=False,
        policy_unknown=False,
    )

    assert determine_overall_state(evaluation) == "OUT_OF_STATUS"


def test_decision_matrix_returns_grace_period_when_active_and_not_overridden():
    evaluation = ComplianceEvaluation(
        timeline_passes=True,
        timeline_violation=False,
        timeline_warning_active=False,
        timeline_grace_period_active=True,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=True,
        policy_fails=False,
        policy_unclear=False,
        policy_unknown=False,
    )

    assert determine_overall_state(evaluation) == "GRACE_PERIOD"


def test_decision_matrix_returns_unknown_for_incomplete_evidence_without_hard_failure():
    evaluation = ComplianceEvaluation(
        timeline_passes=False,
        timeline_violation=False,
        timeline_warning_active=False,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=True,
        policy_passes=False,
        policy_fails=False,
        policy_unclear=False,
        policy_unknown=True,
    )

    assert determine_overall_state(evaluation) == "UNKNOWN"

from app.services.compliance.severity import determine_severity
from app.services.compliance.types import ComplianceEvaluation


def test_severity_violation_for_out_of_status():
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

    assert determine_severity(overall_state="OUT_OF_STATUS", evaluation=evaluation) == "VIOLATION"


def test_severity_warning_for_in_status_with_active_risk():
    evaluation = ComplianceEvaluation(
        timeline_passes=True,
        timeline_violation=False,
        timeline_warning_active=True,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=True,
        policy_fails=False,
        policy_unclear=False,
        policy_unknown=False,
    )

    assert determine_severity(overall_state="IN_STATUS", evaluation=evaluation) == "WARNING"


def test_severity_info_for_clean_in_status_case():
    evaluation = ComplianceEvaluation(
        timeline_passes=True,
        timeline_violation=False,
        timeline_warning_active=False,
        timeline_grace_period_active=False,
        timeline_cap_gap_active=False,
        timeline_unknown=False,
        policy_passes=True,
        policy_fails=False,
        policy_unclear=False,
        policy_unknown=False,
    )

    assert determine_severity(overall_state="IN_STATUS", evaluation=evaluation) == "INFO"

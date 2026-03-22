from app.services.compliance.types import ComplianceEvaluation, FinalComplianceRecord


def test_final_compliance_record_supports_frontend_ready_shape():
    record = FinalComplianceRecord(
        overall_state="IN_STATUS",
        severity="WARNING",
        action_plan=["Report employer to SEVP by 2026-06-25"],
        audit_summary="85 days of unemployment used; job is directly related to the major.",
    )
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

    assert record.overall_state == "IN_STATUS"
    assert evaluation.timeline_warning_active is True

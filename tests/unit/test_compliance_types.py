from app.services.compliance.types import ComplianceEvaluation, FinalComplianceRecord


def test_final_compliance_record_supports_frontend_ready_shape():
    record = FinalComplianceRecord(
        overall_state="IN_STATUS",
        severity="WARNING",
        action_plan=["Report employer to SEVP by 2026-06-25"],
        audit_summary="Your job is directly related to your major, and your timeline is still within the OPT limit.",
        confidence_points=[
            "85 days remaining on OPT",
            "Job directly relates to your major",
        ],
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
    assert record.confidence_points[0] == "85 days remaining on OPT"
    assert evaluation.timeline_warning_active is True

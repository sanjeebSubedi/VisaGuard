from app.services.timeline.conditional import classify_conditional_clock


def test_conditional_clock_is_not_applicable_without_trigger():
    result = classify_conditional_clock(
        facts={},
        trigger_fields=("cap_gap_end_date",),
        required_fields=("cap_gap_end_date",),
    )

    assert result.status == "not_applicable"
    assert result.missing_prerequisites == []


def test_conditional_clock_is_insufficient_when_triggered_but_incomplete():
    result = classify_conditional_clock(
        facts={"has_cap_gap_extension": "true"},
        trigger_fields=("has_cap_gap_extension", "cap_gap_end_date"),
        required_fields=("cap_gap_end_date",),
    )

    assert result.status == "insufficient_data"
    assert result.missing_prerequisites == ["cap_gap_end_date"]


def test_conditional_clock_is_ready_when_trigger_and_required_data_exist():
    result = classify_conditional_clock(
        facts={"cap_gap_end_date": "2026-09-30"},
        trigger_fields=("has_cap_gap_extension", "cap_gap_end_date"),
        required_fields=("cap_gap_end_date",),
    )

    assert result.status == "ready"
    assert result.missing_prerequisites == []

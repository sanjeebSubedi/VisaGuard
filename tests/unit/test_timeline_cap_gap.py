from app.services.timeline.clocks.cap_gap import evaluate_cap_gap


def test_cap_gap_returns_not_applicable_without_cap_gap_inputs():
    result = evaluate_cap_gap(facts={}, evaluation_date="2026-03-20")

    assert result.status == "not_applicable"


def test_cap_gap_returns_insufficient_data_when_triggered_without_end_date():
    result = evaluate_cap_gap(
        facts={"has_cap_gap_extension": "true"},
        evaluation_date="2026-03-20",
    )

    assert result.status == "insufficient_data"
    assert result.missing_prerequisites == ["cap_gap_end_date"]


def test_cap_gap_uses_explicit_cap_gap_end_date_when_present():
    result = evaluate_cap_gap(
        facts={"cap_gap_end_date": "2026-09-30"},
        evaluation_date="2026-08-15",
    )

    assert result.status == "active"
    assert result.relevant_dates["cap_gap_end"] == "2026-09-30"
    assert result.days_remaining == 46

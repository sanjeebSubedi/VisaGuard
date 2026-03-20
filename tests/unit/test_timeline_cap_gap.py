from app.services.timeline.clocks.cap_gap import evaluate_cap_gap


def test_cap_gap_returns_insufficient_data_without_cap_gap_inputs():
    result = evaluate_cap_gap(facts={}, evaluation_date="2026-03-20")

    assert result.status == "insufficient_data"


def test_cap_gap_uses_explicit_cap_gap_end_date_when_present():
    result = evaluate_cap_gap(
        facts={"cap_gap_end_date": "2026-09-30"},
        evaluation_date="2026-08-15",
    )

    assert result.status == "active"
    assert result.relevant_dates["cap_gap_end"] == "2026-09-30"
    assert result.days_remaining == 46

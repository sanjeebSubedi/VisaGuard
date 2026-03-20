from app.services.timeline.clocks.grace_periods import evaluate_grace_period


def test_grace_period_uses_program_end_date_when_present():
    result = evaluate_grace_period(
        facts={"program_end_date": "2026-12-31"},
        evaluation_date="2027-01-10",
    )

    assert result.status == "active"
    assert result.relevant_dates["grace_period_end"] == "2027-03-01"
    assert result.days_remaining == 50


def test_grace_period_returns_insufficient_data_without_program_end():
    result = evaluate_grace_period(
        facts={},
        evaluation_date="2027-01-10",
    )

    assert result.status == "insufficient_data"

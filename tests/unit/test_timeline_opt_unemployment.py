from app.services.timeline.clocks.opt_unemployment import evaluate_opt_unemployment


def test_opt_unemployment_returns_insufficient_data_without_required_dates():
    result = evaluate_opt_unemployment(
        facts={"card_end_date": "2027-08-19"},
        evaluation_date="2026-03-20",
    )

    assert result.status == "insufficient_data"
    assert "card_start_date" in result.missing_prerequisites


def test_opt_unemployment_computes_days_remaining_from_start_dates():
    result = evaluate_opt_unemployment(
        facts={
            "card_start_date": "2026-01-01",
            "start_date": "2026-01-20",
        },
        evaluation_date="2026-03-20",
    )

    assert result.status == "active"
    assert result.limit_days == 90
    assert result.days_remaining == 71

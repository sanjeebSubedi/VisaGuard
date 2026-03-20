from app.services.timeline.clocks.stem_opt_unemployment import evaluate_stem_opt_unemployment


def test_stem_opt_unemployment_uses_150_day_limit():
    result = evaluate_stem_opt_unemployment(
        facts={
            "card_start_date": "2026-01-01",
            "start_date": "2026-03-01",
        },
        evaluation_date="2026-03-20",
    )

    assert result.limit_days == 150
    assert result.days_remaining == 91


def test_stem_opt_unemployment_returns_insufficient_data_when_start_date_missing():
    result = evaluate_stem_opt_unemployment(
        facts={"card_start_date": "2026-01-01"},
        evaluation_date="2026-03-20",
    )

    assert result.status == "insufficient_data"
    assert "start_date" in result.missing_prerequisites

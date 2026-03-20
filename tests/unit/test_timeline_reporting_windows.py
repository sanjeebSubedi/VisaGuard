from app.services.timeline.clocks.reporting_windows import evaluate_reporting_windows


def test_reporting_window_returns_insufficient_data_when_trigger_missing():
    result = evaluate_reporting_windows(facts={}, evaluation_date="2026-03-20")

    assert result.status == "insufficient_data"


def test_reporting_window_uses_start_date_plus_ten_days():
    result = evaluate_reporting_windows(
        facts={"start_date": "2026-04-27"},
        evaluation_date="2026-05-01",
    )

    assert result.status == "active"
    assert result.relevant_dates["report_deadline"] == "2026-05-07"
    assert result.days_remaining == 6

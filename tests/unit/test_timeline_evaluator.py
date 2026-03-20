from app.services.timeline.evaluator import evaluate_timeline
from app.services.timeline.prerequisites import require_fields


def test_require_fields_reports_missing_inputs():
    values = {"card_end_date": "2027-08-19"}

    missing = require_fields(values, "card_start_date", "card_end_date")

    assert missing == ["card_start_date"]


def test_evaluate_timeline_returns_inputs_and_status():
    result = evaluate_timeline(
        facts={
            "program_end_date": "2026-12-31",
            "card_start_date": "2026-01-01",
            "card_end_date": "2027-12-31",
            "start_date": "2026-01-20",
        },
        evaluation_date="2026-03-20",
    )

    assert "timeline_inputs" in result
    assert "timeline_status" in result
    assert result["timeline_status"].current_phase == "opt_active"

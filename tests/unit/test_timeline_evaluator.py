from app.services.timeline.prerequisites import require_fields


def test_require_fields_reports_missing_inputs():
    values = {"card_end_date": "2027-08-19"}

    missing = require_fields(values, "card_start_date", "card_end_date")

    assert missing == ["card_start_date"]

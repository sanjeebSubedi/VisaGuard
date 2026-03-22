from app.services.timeline.evaluator import evaluate_timeline


def test_timeline_manager_integration_returns_valid_status_shape():
    result = evaluate_timeline(
        facts={
            "program_end_date": "2026-12-31",
            "card_start_date": "2026-01-01",
            "card_end_date": "2027-12-31",
            "start_date": "2026-01-20",
        },
        evaluation_date="2027-01-10",
    )

    assert "current_phase" in result["timeline_status"].model_dump()
    assert "clocks" in result["timeline_status"].model_dump()


def test_timeline_manager_marks_untriggered_cap_gap_as_not_applicable():
    result = evaluate_timeline(
        facts={
            "program_end_date": "2026-12-31",
            "card_start_date": "2026-01-01",
            "card_end_date": "2027-12-31",
            "start_date": "2026-01-20",
            "category": "C03B",
        },
        evaluation_date="2026-04-01",
    )

    assert result["timeline_status"].current_phase == "opt_active"
    assert result["timeline_status"].clocks["cap_gap"].status == "not_applicable"

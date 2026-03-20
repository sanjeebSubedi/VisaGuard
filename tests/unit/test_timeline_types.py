from app.services.timeline.types import ClockResult, TimelineStatus


def test_timeline_status_supports_insufficient_data_clock():
    status = TimelineStatus(
        current_phase="unknown",
        clocks={
            "opt_unemployment": ClockResult(
                status="insufficient_data",
                relevant_dates={},
                missing_prerequisites=["card_start_date"],
            )
        },
        deadlines=[],
        risk_flags=[],
        action_items=[],
    )

    assert status.clocks["opt_unemployment"].status == "insufficient_data"

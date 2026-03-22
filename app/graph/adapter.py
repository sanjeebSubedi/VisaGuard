from __future__ import annotations

from app.db.models import StudentStateSnapshot


def build_workflow_state(*, snapshot: StudentStateSnapshot, evaluation_date: str, user_profile: dict | None = None) -> dict:
    state = {
        "extracted_data": dict(snapshot.snapshot_payload),
        "evaluation_date": evaluation_date,
    }
    if user_profile is not None:
        state["user_profile"] = user_profile
    return state

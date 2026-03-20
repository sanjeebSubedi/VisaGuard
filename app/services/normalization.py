from __future__ import annotations

from dataclasses import dataclass, field

from app.services.extractors.base import ExtractedFact
from app.services.review_engine import ReviewItemResult


PRECEDENCE = {
    "employment_authorization": ["ead", "offer_letter", "i20"],
    "academic_program": ["i20", "ead", "offer_letter"],
    "employment_offer": ["offer_letter", "ead", "i20"],
}

FIELD_GROUPS = {
    "employment_authorized_until": "employment_authorization",
    "program_start_date": "academic_program",
    "cip_code": "academic_program",
    "school_name": "academic_program",
    "employer_name": "employment_offer",
    "job_title": "employment_offer",
    "employment_start_date": "employment_offer",
}


@dataclass
class SnapshotResult:
    payload: dict[str, str] = field(default_factory=dict)
    eligibility_map: dict[str, bool] = field(default_factory=dict)
    provenance_map: dict[str, str] = field(default_factory=dict)
    review_items: list[ReviewItemResult] = field(default_factory=list)
def _build_snapshot(
    facts_by_document_type: dict[str, list[ExtractedFact]],
    validation_results: dict[str, dict[str, list[str]]],
) -> SnapshotResult:
    snapshot = SnapshotResult()
    grouped: dict[str, list[tuple[str, ExtractedFact]]] = {}
    for document_type, facts in facts_by_document_type.items():
        for fact in facts:
            grouped.setdefault(fact.field_name, []).append((document_type, fact))

    for field_name, candidates in grouped.items():
        precedence = PRECEDENCE.get(FIELD_GROUPS.get(field_name, "employment_offer"), [])
        sorted_candidates = sorted(
            candidates,
            key=lambda item: precedence.index(item[0]) if item[0] in precedence else len(precedence),
        )
        winner_type, winner_fact = sorted_candidates[0]
        snapshot.payload[field_name] = winner_fact.value
        snapshot.provenance_map[field_name] = f"{winner_type}:{winner_fact.source_location}"

        conflicting_values = {fact.value for _, fact in candidates}
        has_conflict = len(conflicting_values) > 1
        eligible = winner_fact.confidence >= 0.95 and winner_fact.status == "provisional" and not has_conflict
        snapshot.eligibility_map[field_name] = eligible

        if has_conflict:
            snapshot.review_items.append(ReviewItemResult(review_type="conflict", field_name=field_name))
        elif winner_fact.confidence < 0.95:
            snapshot.review_items.append(ReviewItemResult(review_type="low_confidence", field_name=field_name))

    for document_validation in validation_results.values():
        for field_name in document_validation.get("missing_fields", []):
            snapshot.review_items.append(ReviewItemResult(review_type="missing_field", field_name=field_name))
        for field_name in document_validation.get("invalid_fields", []):
            snapshot.review_items.append(ReviewItemResult(review_type="invalid_field", field_name=field_name))

    return snapshot


def build_snapshot(
    facts_by_document_type: dict[str, list[ExtractedFact]],
    validation_results: dict[str, dict[str, list[str]]] | None = None,
) -> SnapshotResult:
    return _build_snapshot(facts_by_document_type, validation_results or {})

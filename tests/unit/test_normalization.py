from app.services.normalization import build_snapshot
from app.services.extractors.base import ExtractedFact


def test_build_snapshot_prefers_ead_for_authorization_dates_and_blocks_conflicts():
    facts = [
        ExtractedFact(field_name="card_end_date", value="2027-08-19", confidence=0.98, source_location="ead:1"),
        ExtractedFact(field_name="card_end_date", value="2027-08-01", confidence=0.91, source_location="offer_letter:1"),
    ]

    snapshot = build_snapshot(facts_by_document_type={"ead": [facts[0]], "offer_letter": [facts[1]]})

    assert snapshot.payload["card_end_date"] == "2027-08-19"
    assert snapshot.eligibility_map["card_end_date"] is False
    assert snapshot.review_items[0].review_type == "conflict"


def test_build_snapshot_adds_missing_field_review_items_from_validation_results():
    result = build_snapshot(
        facts_by_document_type={"offer_letter": []},
        validation_results={"offer_letter": {"missing_fields": ["start_date"], "invalid_fields": []}},
    )

    assert any(
        item.review_type == "missing_field" and item.field_name == "start_date"
        for item in result.review_items
    )

from app.services.normalization import build_snapshot
from app.services.extractors.base import ExtractedFact


def test_build_snapshot_prefers_ead_for_authorization_dates_and_blocks_conflicts():
    facts = [
        ExtractedFact(field_name="employment_authorized_until", value="2027-08-19", confidence=0.98, source_location="ead:1"),
        ExtractedFact(field_name="employment_authorized_until", value="2027-08-01", confidence=0.91, source_location="offer_letter:1"),
    ]

    snapshot = build_snapshot(facts_by_document_type={"ead": [facts[0]], "offer_letter": [facts[1]]})

    assert snapshot.payload["employment_authorized_until"] == "2027-08-19"
    assert snapshot.eligibility_map["employment_authorized_until"] is False
    assert snapshot.review_items[0].review_type == "conflict"

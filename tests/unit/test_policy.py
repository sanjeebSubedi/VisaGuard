from app.services.policy import get_document_policy


def test_offer_letter_policy_requires_retained_redacted_text():
    policy = get_document_policy("offer_letter")
    assert policy.allowed_kind == "pdf"
    assert policy.persist_retained_text is True
    assert policy.redact_retained_text is True

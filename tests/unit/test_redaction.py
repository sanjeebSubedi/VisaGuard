from app.services.redaction import redact_direct_identifiers


def test_redaction_removes_direct_identifiers_only():
    text = """
    Student Name: Ada Lovelace
    SEVIS ID: N0012345678
    Email: ada@example.com
    Employer: OpenAI
    Start Date: 2026-09-01
    """

    redacted = redact_direct_identifiers(text)

    assert "Ada Lovelace" not in redacted.text
    assert "N0012345678" not in redacted.text
    assert "ada@example.com" not in redacted.text
    assert "OpenAI" in redacted.text

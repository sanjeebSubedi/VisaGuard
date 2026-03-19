def test_upload_snapshot_and_review_endpoints_never_expose_direct_identifiers(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={
            "file": (
                "offer.pdf",
                b"Employer: OpenAI\nTitle: Research Intern\nStart Date: 2026-09-01\nStudent Name: Ada Lovelace\nEmail: ada@example.com\nPhone: 555-111-2222\nSEVIS ID: N0012345678\n",
                "application/pdf",
            )
        },
    )

    upload_body = response.text
    snapshot = client.get("/api/intake/users/student-1/snapshot").text
    review_items = client.get("/api/intake/users/student-1/review-items").text

    assert "encrypted_original_uri" not in upload_body
    assert "ada@example.com" not in upload_body
    assert "555-111-2222" not in upload_body
    assert "N0012345678" not in snapshot
    assert "Ada Lovelace" not in review_items

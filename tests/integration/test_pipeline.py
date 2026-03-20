OFFER_LETTER_FIXTURE_BYTES = b"Employer: OpenAI\nTitle: Research Intern\nStart Date: 2026-09-01\nEmail: ada@example.com\n"


def test_processing_pipeline_persists_artifacts_and_snapshot(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", OFFER_LETTER_FIXTURE_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["redaction_status"] == "completed"
    assert body["extraction_status"] == "completed"

    snapshot = client.get("/api/intake/users/student-1/snapshot").json()
    assert snapshot["snapshot_payload"]["employer_name"] == "OpenAI"


def test_parse_failure_marks_document_parse_failed(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.parse_with_docling",
        lambda **_: (_ for _ in ()).throw(Exception("parse boom")),
    )

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", b"fake-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "parse_failed"

from pathlib import Path

from sqlalchemy import select

from app.db.models import Document

I20_FIXTURE_BYTES = b"Program Start Date: 2026-08-20\nProgram End Date: 2028-05-15\n"
OFFER_LETTER_FIXTURE_BYTES = b"Employer: OpenAI\nTitle: Research Intern\nStart Date: 2026-09-01\nEmail: ada@example.com\n"
I20_PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
EAD_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
OFFER_LETTER_PDF_BYTES = b"%PDF-1.7\n2 0 obj\n<< /Type /Page >>\nendobj\n"


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


def test_i20_persists_facts_only_without_retained_text(client, db_session, monkeypatch, tmp_path):
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", I20_FIXTURE_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "completed"

    document = db_session.scalar(select(Document).where(Document.id == body["id"]))

    assert document is not None
    assert document.retained_text_uri is None
    assert not (storage_root / "retained").exists()


def test_offer_letter_persists_redacted_retained_text(client, db_session, monkeypatch, tmp_path):
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", OFFER_LETTER_FIXTURE_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()

    document = db_session.scalar(select(Document).where(Document.id == body["id"]))

    assert document is not None
    assert document.retained_text_uri == f"retained/document-{document.id}.txt"

    retained_text = Path(storage_root / document.retained_text_uri).read_text()

    assert "[REDACTED_EMAIL]" in retained_text
    assert "ada@example.com" not in retained_text


def test_snapshot_contract_still_returns_canonical_fields_after_docling_upgrade(client):
    client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", I20_PDF_BYTES, "application/pdf")},
    )
    client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "ead"},
        files={"file": ("ead.png", EAD_IMAGE_BYTES, "image/png")},
    )
    client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", OFFER_LETTER_PDF_BYTES, "application/pdf")},
    )

    snapshot = client.get("/api/intake/users/student-1/snapshot")

    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["snapshot_payload"]["program_start_date"] == "2026-08-20"
    assert body["snapshot_payload"]["employment_authorized_until"] == "2027-08-19"
    assert body["snapshot_payload"]["employer_name"] == "OpenAI"

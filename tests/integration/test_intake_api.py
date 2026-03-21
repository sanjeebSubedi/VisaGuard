from sqlalchemy import create_engine, inspect

from app.db.base import Base


def test_upload_creates_document_record(client, db_session):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("form-i20.pdf", b"Program Start Date: 2026-08-20\nCIP Code: 11.0101", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "i20"
    assert body["parse_status"] == "completed"


def test_upload_rejects_pdf_for_ead(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "ead"},
        files={"file": ("ead.pdf", b"fake", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_accepts_png_for_ead(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "ead"},
        files={"file": ("ead.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 201


def test_upload_fails_when_ollama_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.LLMExtractionService.extract",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ollama unavailable")),
    )

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", b"pdf", "application/pdf")},
    )

    assert response.status_code == 500


def test_initialize_database_creates_tables_for_manual_local_runs(tmp_path, monkeypatch):
    import app.main as main_module

    engine = create_engine(f"sqlite:///{tmp_path / 'manual.db'}", future=True)
    Base.metadata.drop_all(engine)
    monkeypatch.setattr(main_module, "build_engine", lambda settings=None: engine)

    main_module.initialize_database()

    inspector = inspect(engine)
    assert "documents" in inspector.get_table_names()



def test_manual_ead_entry_creates_document_and_snapshot(client, db_session):
    response = client.post(
        "/api/intake/ead/manual",
        json={
            "user_id": "student-1",
            "alien_registration_number": "A123456789",
            "category": "C03B",
            "card_start_date": "2026-08-20",
            "card_end_date": "2027-08-19",
            "card_number": "EAD1234567",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "ead"
    assert body["parse_status"] == "skipped"
    assert body["extraction_status"] == "completed"

    snapshot_response = client.get("/api/intake/users/student-1/snapshot")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["snapshot_payload"]["alien_registration_number"] == "A123456789"
    assert snapshot["provenance_map"]["alien_registration_number"].startswith("ead:manual:")


def test_manual_ead_entry_rejects_invalid_dates(client):
    response = client.post(
        "/api/intake/ead/manual",
        json={
            "user_id": "student-1",
            "alien_registration_number": "A123456789",
            "category": "C03B",
            "card_start_date": "08/20/2026",
            "card_end_date": "2027-08-19",
        },
    )

    assert response.status_code == 422

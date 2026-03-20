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

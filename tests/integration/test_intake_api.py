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

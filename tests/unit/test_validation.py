import pytest

from app.services.validation import UploadValidationError, validate_upload


def test_validate_upload_rejects_pdf_for_ead():
    with pytest.raises(UploadValidationError):
        validate_upload(document_type="ead", filename="card.pdf", content_type="application/pdf")

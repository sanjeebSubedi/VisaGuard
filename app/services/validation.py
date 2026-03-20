from __future__ import annotations

from app.services.policy import get_document_policy


class UploadValidationError(ValueError):
    pass


PDF_CONTENT_TYPES = {"application/pdf"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff", "image/bmp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def validate_upload(*, document_type: str, filename: str, content_type: str) -> None:
    policy = get_document_policy(document_type)
    extension = "." + filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    if policy.allowed_kind == "pdf":
        if content_type not in PDF_CONTENT_TYPES or extension not in PDF_EXTENSIONS:
            raise UploadValidationError(f"{document_type} uploads must be PDF files")
        return

    if policy.allowed_kind == "image":
        if content_type not in IMAGE_CONTENT_TYPES or extension not in IMAGE_EXTENSIONS:
            raise UploadValidationError(f"{document_type} uploads must be image files")
        return

    raise UploadValidationError(f"Unsupported upload policy for {document_type}")

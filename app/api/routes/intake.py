from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.schemas.intake import DocumentResponse
from app.db.models import Document
from app.db.session import get_db_session
from app.services.fingerprints import sha256_bytes
from app.services.storage import ArtifactStorage
from app.core.config import Settings

router = APIRouter(prefix="/api/intake", tags=["intake"])
ALLOWED_DOCUMENT_TYPES = {"i20", "ead", "offer_letter"}


@router.post("/documents", status_code=201, response_model=DocumentResponse)
def upload_document(
    user_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> Document:
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported document type")

    content = file.file.read()
    fingerprint = sha256_bytes(content)
    settings = Settings()
    storage = ArtifactStorage(root=settings.storage_root, encryption_key=settings.encryption_key)
    original_uri = storage.store_original(user_id, file.filename or "upload.bin", content)

    document = Document(
        user_id=user_id,
        document_type=document_type,
        encrypted_original_uri=original_uri,
        file_fingerprint=fingerprint,
        parse_status="pending",
        redaction_status="pending",
        extraction_status="pending",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

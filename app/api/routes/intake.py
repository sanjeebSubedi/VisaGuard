from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from app.api.schemas.intake import DocumentResponse, ManualEADEntryRequest, ReviewItemResponse, SnapshotResponse
from app.core.config import Settings
from app.db.models import Document, ReviewItem, StudentStateSnapshot
from app.db.session import get_db_session
from app.services.fingerprints import sha256_bytes
from app.services.pipeline import DocumentPipeline
from app.services.storage import ArtifactStorage
from app.services.validation import UploadValidationError, validate_upload

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

    try:
        validate_upload(
            document_type=document_type,
            filename=file.filename or "upload.bin",
            content_type=file.content_type or "application/octet-stream",
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    pipeline = DocumentPipeline(session=session, storage=storage)
    return pipeline.process_uploaded_document(
        document,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
    )


@router.post("/ead/manual", status_code=201, response_model=DocumentResponse)
def create_manual_ead_entry(
    payload: ManualEADEntryRequest = Body(...),
    session: Session = Depends(get_db_session),
) -> Document:
    document = Document(
        user_id=payload.user_id,
        document_type="ead",
        encrypted_original_uri=None,
        file_fingerprint=None,
        parse_status="pending",
        redaction_status="pending",
        extraction_status="pending",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    settings = Settings()
    storage = ArtifactStorage(root=settings.storage_root, encryption_key=settings.encryption_key)
    pipeline = DocumentPipeline(session=session, storage=storage)

    return pipeline.process_manual_ead_entry(
        document,
        values={
            "alien_registration_number": payload.alien_registration_number,
            "category": payload.category,
            "card_start_date": payload.card_start_date,
            "card_end_date": payload.card_end_date,
            "card_number": payload.card_number,
        },
    )


@router.get("/users/{user_id}/snapshot", response_model=SnapshotResponse)
def get_snapshot(user_id: str, session: Session = Depends(get_db_session)) -> StudentStateSnapshot:
    snapshot = session.scalar(
        select(StudentStateSnapshot)
        .where(StudentStateSnapshot.user_id == user_id)
        .order_by(StudentStateSnapshot.version.desc())
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.get("/users/{user_id}/review-items", response_model=list[ReviewItemResponse])
def get_review_items(user_id: str, session: Session = Depends(get_db_session)) -> list[ReviewItem]:
    return session.scalars(select(ReviewItem).where(ReviewItem.user_id == user_id)).all()

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentFact, ReviewItem, StudentStateSnapshot
from app.services.extractors.router import get_extractor
from app.services.normalization import build_snapshot
from app.services.parsing.docling_parser import DoclingParseError, parse_with_docling
from app.services.policy import get_document_policy
from app.services.redaction import redact_direct_identifiers
from app.services.storage import ArtifactStorage


class DocumentPipeline:
    def __init__(self, session: Session, storage: ArtifactStorage) -> None:
        self.session = session
        self.storage = storage

    def process_uploaded_document(self, document: Document, *, filename: str, content_type: str) -> Document:
        policy = get_document_policy(document.document_type)
        try:
            parsed = parse_with_docling(
                file_bytes=self.storage.load_original(document.encrypted_original_uri or ""),
                filename=filename,
                content_type=content_type,
            )
        except Exception as exc:
            document.parse_status = "parse_failed"
            document.parse_error_message = str(exc)
            document.redaction_status = "pending"
            document.extraction_status = "pending"
            document.parser_version = "docling-adapter-v1"
            self.session.commit()
            self.session.refresh(document)
            return document

        parse_artifact_uri = Path("parsed") / f"document-{document.id}.json"
        self.storage.write_json(parse_artifact_uri, parsed.raw_payload)

        redacted = redact_direct_identifiers(parsed.text)
        redacted_artifact_uri = Path("redacted") / f"document-{document.id}.txt"
        self.storage.write_text(redacted_artifact_uri, redacted.text)

        document.parse_status = "completed"
        document.redaction_status = "completed"
        document.parse_artifact_uri = str(parse_artifact_uri)
        document.redacted_artifact_uri = str(redacted_artifact_uri)
        document.parser_version = "docling-adapter-v1"

        extractor = get_extractor(policy.document_type)
        extracted_facts = extractor.extract(redacted.text)
        document.extractor_version = "rule-based-v1"
        document.extraction_status = "completed"

        for fact in extracted_facts:
            self.session.add(
                DocumentFact(
                    document_id=document.id,
                    field_name=fact.field_name,
                    value=fact.value,
                    normalized_value=None,
                    confidence=fact.confidence,
                    status=fact.status,
                    source_location=fact.source_location,
                )
            )

        self.session.flush()
        self._refresh_snapshot(document.user_id)
        self.session.commit()
        self.session.refresh(document)
        return document

    def _refresh_snapshot(self, user_id: str) -> None:
        documents = self.session.scalars(select(Document).where(Document.user_id == user_id)).all()
        facts_by_document_type: dict[str, list] = {}
        for document in documents:
            facts = self.session.scalars(select(DocumentFact).where(DocumentFact.document_id == document.id)).all()
            facts_by_document_type.setdefault(document.document_type, []).extend(facts)

        snapshot_result = build_snapshot(facts_by_document_type)
        latest_version = self.session.scalar(
            select(StudentStateSnapshot.version)
            .where(StudentStateSnapshot.user_id == user_id)
            .order_by(StudentStateSnapshot.version.desc())
            .limit(1)
        )
        next_version = (latest_version or 0) + 1

        snapshot = StudentStateSnapshot(
            user_id=user_id,
            version=next_version,
            snapshot_payload=snapshot_result.payload,
            field_eligibility_map=snapshot_result.eligibility_map,
            provenance_map=snapshot_result.provenance_map,
        )
        self.session.add(snapshot)
        self.session.flush()

        self.session.execute(delete(ReviewItem).where(ReviewItem.user_id == user_id))
        for item in snapshot_result.review_items:
            self.session.add(
                ReviewItem(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    review_type=item.review_type,
                    field_name=item.field_name,
                    priority=item.priority,
                    assigned_role=item.assigned_role,
                    resolution_status=item.resolution_status,
                )
            )

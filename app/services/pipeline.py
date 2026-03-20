from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentFact, ReviewItem, StudentStateSnapshot
from app.services.llm.extractor import LLMExtractionService
from app.services.normalization import build_snapshot
from app.services.parsing.docling_parser import parse_with_docling
from app.services.policy import get_document_policy
from app.services.redaction import redact_direct_identifiers
from app.services.storage import ArtifactStorage
from app.services.validation_rules import validate_extracted_values


class DocumentPipeline:
    def __init__(self, session: Session, storage: ArtifactStorage) -> None:
        self.session = session
        self.storage = storage
        self.llm_extractor = LLMExtractionService()

    def process_uploaded_document(self, document: Document, *, filename: str, content_type: str) -> Document:
        policy = get_document_policy(document.document_type)
        document.parse_artifact_uri = None
        document.redacted_artifact_uri = None
        document.retained_text_uri = None
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

        document.parse_status = "completed"
        document.parser_version = "docling-adapter-v1"
        document.redaction_status = "skipped"

        extraction_text = parsed.text
        if policy.persist_retained_text:
            redacted = redact_direct_identifiers(parsed.text)
            document.retained_text_uri = self.storage.write_retained_text(document.id, redacted.text)
            document.redaction_status = "completed"

        outcome = self.llm_extractor.extract(document_type=policy.document_type, parsed_text=extraction_text)
        validate_extracted_values(document_type=policy.document_type, values=outcome.values)
        document.llm_model_name = outcome.model_name
        document.llm_prompt_version = outcome.prompt_version
        document.llm_raw_response_uri = self.storage.write_llm_response(document.id, outcome.raw_json)
        document.extractor_version = "ollama-v1"
        document.extraction_status = "completed"

        for field_name, value in outcome.values.items():
            if value is None:
                continue
            self.session.add(
                DocumentFact(
                    document_id=document.id,
                    field_name=field_name,
                    value=value,
                    normalized_value=None,
                    confidence=0.95,
                    status="provisional",
                    source_location=f"llm:{field_name}",
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
        validation_results: dict[str, dict[str, list[str]]] = {}
        for document in documents:
            facts = self.session.scalars(select(DocumentFact).where(DocumentFact.document_id == document.id)).all()
            facts_by_document_type.setdefault(document.document_type, []).extend(facts)
            values = {fact.field_name: fact.value for fact in facts}
            document_validation = validate_extracted_values(document.document_type, values)
            current = validation_results.setdefault(
                document.document_type,
                {"missing_fields": [], "invalid_fields": []},
            )
            for field_name in document_validation.missing_fields:
                if field_name not in current["missing_fields"]:
                    current["missing_fields"].append(field_name)
            for field_name in document_validation.invalid_fields:
                if field_name not in current["invalid_fields"]:
                    current["invalid_fields"].append(field_name)

        snapshot_result = build_snapshot(facts_by_document_type, validation_results=validation_results)
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

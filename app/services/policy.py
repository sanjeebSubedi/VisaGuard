from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPolicy:
    document_type: str
    allowed_kind: str
    persist_retained_text: bool
    redact_retained_text: bool


POLICIES = {
    "i20": DocumentPolicy("i20", "pdf", False, False),
    "ead": DocumentPolicy("ead", "image", False, False),
    "offer_letter": DocumentPolicy("offer_letter", "pdf", True, True),
}


def get_document_policy(document_type: str) -> DocumentPolicy:
    try:
        return POLICIES[document_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported document type: {document_type}") from exc

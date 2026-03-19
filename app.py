import os
from pathlib import Path

import streamlit as st

from app.db.database import get_session, init_db, save_ead, save_i20, save_offer_letter
from app.services.document_processor import (
    extract_ead_from_text,
    extract_i20_from_text,
    extract_offer_letter_from_text,
)
from app.services.ingestion import IngestionService

DOC_TYPES = {
    "I-20": "i20",
    "EAD": "ead",
    "Offer Letter": "offer_letter",
}


def _persist_upload(upload, uploads_dir: Path) -> Path:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(upload.name).name
    target = uploads_dir / safe_name
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while True:
            candidate = uploads_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                target = candidate
                break
            counter += 1
    target.write_bytes(upload.getbuffer())
    return target


def main() -> None:
    st.set_page_config(page_title="VisaGuard", layout="centered")
    st.title("VisaGuard")
    st.write(
        "Upload your OPT documents to extract fields locally, scrub PII, and store the "
        "minimum required data for I-983 prep."
    )

    doc_label = st.selectbox("Document type", list(DOC_TYPES.keys()))
    uploaded = st.file_uploader(
        "Upload a document",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    )

    if uploaded is None:
        return

    use_llm_redaction = st.checkbox(
        "Use local LLM for extra redaction (slower)",
        value=True,
    )
    model_name = os.getenv("VISAGUARD_OLLAMA_MODEL", "qwen3:4b-instruct")
    st.caption(f"Local model: {model_name}")

    if st.button("Process", type="primary"):
        try:
            uploads_dir = Path("data/uploads")
            file_path = _persist_upload(uploaded, uploads_dir)

            ingestion = IngestionService(
                use_cache=True,
                use_llm_redaction=use_llm_redaction,
                llm_model=model_name,
            )
            parsed = ingestion.ingest_file(file_path, doc_type=DOC_TYPES[doc_label])

            if not parsed.raw_text:
                st.error("Failed to parse document text.")
                return

            if DOC_TYPES[doc_label] == "i20":
                extracted = extract_i20_from_text(parsed.raw_text)
                fields = extracted.model_dump()
                save_func = save_i20
            elif DOC_TYPES[doc_label] == "ead":
                extracted = extract_ead_from_text(parsed.raw_text)
                fields = extracted.model_dump()
                save_func = save_ead
            else:
                extracted = extract_offer_letter_from_text(parsed.raw_text)
                fields = extracted.model_dump()
                save_func = save_offer_letter

            init_db()
            with get_session() as session:
                doc_id = save_func(session, str(file_path), parsed.content_hash, fields)

            st.success(f"Saved to local database. Record ID: {doc_id}")
            st.subheader("Extracted Fields")
            st.json(fields)

            with st.expander("Scrubbed Text (PII redacted)"):
                st.write(parsed.scrubbed_text)

        except Exception as exc:
            st.error(f"Processing failed: {exc}")


if __name__ == "__main__":
    main()

from app.db.models import Document, StudentStateSnapshot


def test_document_and_snapshot_tables_create(db_session):
    document = Document(user_id="student-1", document_type="i20", parse_status="pending")
    snapshot = StudentStateSnapshot(user_id="student-1", version=1, snapshot_payload={})
    db_session.add_all([document, snapshot])
    db_session.commit()

    assert document.id is not None
    assert snapshot.id is not None


def test_document_can_track_parse_failure_and_retained_text_path(db_session):
    document = Document(
        user_id="student-1",
        document_type="offer_letter",
        parse_status="parse_failed",
        retained_text_uri="retained/offer-letter.txt",
    )
    db_session.add(document)
    db_session.commit()

    assert document.id is not None
    assert document.parse_status == "parse_failed"
    assert document.retained_text_uri == "retained/offer-letter.txt"


def test_document_can_track_llm_debug_metadata(db_session):
    document = Document(
        user_id="student-1",
        document_type="i20",
        llm_model_name="qwen3:4b-instruct",
        llm_prompt_version="v1",
        llm_raw_response_uri="llm/document-1.json",
    )
    db_session.add(document)
    db_session.commit()

    assert document.id is not None
    assert document.llm_model_name == "qwen3:4b-instruct"

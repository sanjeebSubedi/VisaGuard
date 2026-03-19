from app.db.models import Document, StudentStateSnapshot


def test_document_and_snapshot_tables_create(db_session):
    document = Document(user_id="student-1", document_type="i20", parse_status="pending")
    snapshot = StudentStateSnapshot(user_id="student-1", version=1, snapshot_payload={})
    db_session.add_all([document, snapshot])
    db_session.commit()

    assert document.id is not None
    assert snapshot.id is not None

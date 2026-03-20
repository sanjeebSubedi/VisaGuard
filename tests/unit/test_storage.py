from app.services.storage import ArtifactStorage


def test_store_original_encrypts_bytes(tmp_path):
    storage = ArtifactStorage(root=tmp_path, encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    location = storage.store_original("user-1", "offer_letter.pdf", b"secret content")
    raw_bytes = (tmp_path / location).read_bytes()

    assert raw_bytes != b"secret content"
    assert storage.load_original(location) == b"secret content"


def test_write_llm_response_persists_json(tmp_path):
    storage = ArtifactStorage(root=tmp_path, encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    location = storage.write_llm_response(7, {"program_start_date": "2026-08-20"})

    assert (tmp_path / location).exists()

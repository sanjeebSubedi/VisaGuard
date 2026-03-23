from pathlib import Path

from app.services.dso_agent.indexer import build_dso_index
from app.services.dso_agent.retriever import HybridDSORetriever


def test_build_dso_index_writes_chroma_collection(tmp_path):
    federal_dir = tmp_path / "federal"
    federal_dir.mkdir()
    (federal_dir / "travel.md").write_text("# Travel\nStudents may need a travel signature.")
    university_dir = tmp_path / "universities" / "nyu"
    university_dir.mkdir(parents=True)
    (university_dir / "signature.md").write_text("# NYU Travel\nUse OGS portal.")
    output_dir = tmp_path / "chroma"

    result = build_dso_index(
        federal_sources_dir=federal_dir,
        university_sources_root=tmp_path / "universities",
        persist_directory=output_dir,
    )

    assert result.exists()


def test_retriever_can_filter_to_university_scope():
    retriever = HybridDSORetriever.from_documents([
        {"source_id": "fed-1", "title": "Travel", "citation": "8 CFR", "source_type": "federal", "school_key": None, "text": "Travel signatures may be required."},
        {"source_id": "nyu-1", "title": "NYU Travel", "citation": "NYU OGS", "source_type": "university", "school_key": "nyu", "text": "Use the OGS portal for a travel signature."},
    ])
    results = retriever.search("How do I get a travel signature?", scope="university", school_key="nyu")
    assert results[0].source_type == "university"


def test_retriever_can_limit_to_federal_scope():
    retriever = HybridDSORetriever.from_documents([
        {"source_id": "fed-1", "title": "OPT Jobs", "citation": "8 CFR", "source_type": "federal", "school_key": None, "text": "Students may hold multiple jobs on OPT if all employment is qualifying."},
        {"source_id": "nyu-1", "title": "NYU Travel", "citation": "NYU OGS", "source_type": "university", "school_key": "nyu", "text": "Use the OGS portal for a travel signature."},
    ])
    results = retriever.search("Can I work two jobs on OPT?", scope="federal", school_key="nyu")
    assert all(result.source_type == "federal" for result in results)


def test_retriever_can_mix_federal_and_university_results():
    retriever = HybridDSORetriever.from_documents([
        {"source_id": "fed-1", "title": "Travel", "citation": "8 CFR", "source_type": "federal", "school_key": None, "text": "Travel signatures may be needed for re-entry."},
        {"source_id": "nyu-1", "title": "NYU Travel", "citation": "NYU OGS", "source_type": "university", "school_key": "nyu", "text": "Request your travel signature through the OGS portal."},
    ])
    results = retriever.search("How do I travel internationally on OPT?", scope="mixed", school_key="nyu")
    assert {result.source_type for result in results} == {"federal", "university"}

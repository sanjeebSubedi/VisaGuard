from pathlib import Path

from app.services.policy_agent.indexer import build_policy_index
from app.services.policy_agent.retriever import HybridPolicyRetriever


DATASET_PATH = Path('data/policy/cip_codes.json')
SOURCES_DIR = Path('data/policy/sources')


def test_hybrid_retriever_returns_cip_and_policy_sources(tmp_path):
    index_path = tmp_path / 'policy_index.json'
    build_policy_index(
        cip_dataset_path=DATASET_PATH,
        policy_sources_dir=SOURCES_DIR,
        output_path=index_path,
    )

    retriever = HybridPolicyRetriever.load(index_path)
    results = retriever.search('computer science software engineering directly related major area of study', top_k=4)

    source_types = {result.source_type for result in results}

    assert 'cip' in source_types
    assert 'policy' in source_types
    assert results[0].score >= results[-1].score

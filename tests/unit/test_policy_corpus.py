from pathlib import Path

from app.services.policy_agent.corpus import load_policy_sources


SOURCES_DIR = Path('data/policy/sources')


def test_policy_corpus_loads_local_sources_with_metadata():
    sources = load_policy_sources(SOURCES_DIR)

    assert sources
    first = sources[0]
    assert first.source_id
    assert first.title
    assert first.citation
    assert first.source_type == 'policy'
    assert first.text

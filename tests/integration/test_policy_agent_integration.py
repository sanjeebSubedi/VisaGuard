from pathlib import Path

from app.services.policy_agent.agent import PolicyAgent, evaluate_policy_state
from app.services.policy_agent.indexer import build_policy_index


DATASET_PATH = Path('data/policy/cip_codes.json')
SOURCES_DIR = Path('data/policy/sources')


class StubReasoningClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def generate_structured(self, *, model: str, prompt: str, schema=None) -> dict:
        return self._responses.pop(0)


def test_policy_agent_integration_writes_analysis_and_verdict_into_state(tmp_path, fake_embedder):
    index_path = tmp_path / 'policy_index.json'
    build_policy_index(cip_dataset_path=DATASET_PATH, policy_sources_dir=SOURCES_DIR, output_path=index_path, embedder=fake_embedder)
    llm = StubReasoningClient(
        [
            {"summary": "The duties align with computer science training.", "evidence_strength": "strong", "ambiguity_notes": []},
            {"verdict": "directly_related", "confidence": "high", "rationale": {"major_match": "The role uses core computer science knowledge.", "duty_match": "The duties center on backend software engineering.", "policy_basis": "The work applies knowledge gained in the degree program.", "summary": "The position is directly related to the major."}, "cited_source_ids": ["cip-11.0701", "sevp-policy-1004-03"]},
        ]
    )
    agent = PolicyAgent(index_path=index_path, cip_dataset_path=DATASET_PATH, reasoning_client=llm, model_name='test-model', embedder=fake_embedder)

    state = {
        'cip_code': '11.0701',
        'major': 'Computer Science',
        'position_title': 'Backend Software Engineer',
        'job_duties': 'Build backend APIs, distributed systems, and database-backed services.',
    }

    updated_state = evaluate_policy_state(state, agent)

    assert updated_state['policy_analysis']['cip_code'] == '11.0701'
    assert updated_state['policy_verdict']['verdict'] == 'directly_related'

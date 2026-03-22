from pathlib import Path

from app.services.policy_agent.agent import PolicyAgent
from app.services.policy_agent.indexer import build_policy_index


DATASET_PATH = Path('data/policy/cip_codes.json')
SOURCES_DIR = Path('data/policy/sources')


class StubReasoningClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts = []

    def generate_structured(self, *, model: str, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self._responses.pop(0)


def test_policy_agent_generates_analysis_and_verdict(tmp_path):
    index_path = tmp_path / 'policy_index.json'
    build_policy_index(cip_dataset_path=DATASET_PATH, policy_sources_dir=SOURCES_DIR, output_path=index_path)
    llm = StubReasoningClient(
        [
            {"summary": "The duties align with computer science training.", "evidence_strength": "strong", "ambiguity_notes": []},
            {"verdict": "directly_related", "confidence": "high", "rationale": {"major_match": "The role uses core computer science knowledge.", "duty_match": "The duties center on backend software engineering.", "policy_basis": "The work applies knowledge gained in the degree program.", "summary": "The position is directly related to the major."}, "cited_source_ids": ["cip-11.0701", "sevp-policy-1004-03"]},
        ]
    )

    agent = PolicyAgent(index_path=index_path, cip_dataset_path=DATASET_PATH, reasoning_client=llm, model_name='test-model')
    result = agent.evaluate(
        {
            'cip_code': '11.0701',
            'major': 'Computer Science',
            'position_title': 'Backend Software Engineer',
            'job_duties': 'Build backend APIs, distributed systems, and database-backed services.',
        }
    )

    assert result['policy_analysis'].summary.startswith('The duties align')
    assert result['policy_verdict'].verdict == 'directly_related'
    assert result['policy_verdict'].cited_sources[0].source_id == 'cip-11.0701'


def test_policy_agent_returns_insufficient_evidence_for_unknown_cip(tmp_path):
    index_path = tmp_path / 'policy_index.json'
    build_policy_index(cip_dataset_path=DATASET_PATH, policy_sources_dir=SOURCES_DIR, output_path=index_path)

    agent = PolicyAgent(index_path=index_path, cip_dataset_path=DATASET_PATH, reasoning_client=StubReasoningClient([]), model_name='test-model')
    result = agent.evaluate(
        {
            'cip_code': '99.9999',
            'major': 'Unknown Major',
            'position_title': 'Backend Software Engineer',
            'job_duties': 'Build backend APIs.',
        }
    )

    assert result['policy_verdict'].verdict == 'insufficient_policy_evidence'
    assert result['policy_verdict'].confidence == 'low'


def test_policy_agent_filters_citations_to_retrieved_sources(tmp_path):
    index_path = tmp_path / 'policy_index.json'
    build_policy_index(cip_dataset_path=DATASET_PATH, policy_sources_dir=SOURCES_DIR, output_path=index_path)
    llm = StubReasoningClient(
        [
            {"summary": "The duties align with computer science training.", "evidence_strength": "strong", "ambiguity_notes": []},
            {"verdict": "directly_related", "confidence": "medium", "rationale": {"major_match": "Match", "duty_match": "Match", "policy_basis": "Policy match", "summary": "Summary"}, "cited_source_ids": ["cip-11.0701", "invented-source"]},
        ]
    )

    agent = PolicyAgent(index_path=index_path, cip_dataset_path=DATASET_PATH, reasoning_client=llm, model_name='test-model')
    result = agent.evaluate(
        {
            'cip_code': '11.0701',
            'major': 'Computer Science',
            'position_title': 'Backend Software Engineer',
            'job_duties': 'Build backend APIs, distributed systems, and database-backed services.',
        }
    )

    assert [source.source_id for source in result['policy_verdict'].cited_sources] == ['cip-11.0701']

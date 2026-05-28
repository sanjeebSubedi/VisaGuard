from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.embeddings import Embedder
from app.services.policy_agent.cip_loader import CIPDataset, CIPNotFoundError
from app.services.policy_agent.retriever import HybridPolicyRetriever
from app.services.policy_agent.types import (
    PolicyAnalysis,
    PolicyAnalysisPayload,
    PolicyRationale,
    PolicyVerdict,
    PolicyVerdictPayload,
    RetrievedSource,
)


class PolicyAgent:
    def __init__(self, *, index_path: Path, cip_dataset_path: Path, reasoning_client: Any, model_name: str, embedder: Embedder) -> None:
        self._retriever = HybridPolicyRetriever.load(index_path, embedder=embedder)
        self._cip_dataset = CIPDataset.load(cip_dataset_path)
        self._reasoning_client = reasoning_client
        self._model_name = model_name
        prompts_dir = Path(__file__).with_name('prompts')
        self._analysis_prompt = (prompts_dir / 'analysis.txt').read_text().strip()
        self._verdict_prompt = (prompts_dir / 'verdict.txt').read_text().strip()

    def evaluate(self, facts: dict[str, str]) -> dict[str, object]:
        cip_code = facts.get('cip_code')
        if not cip_code:
            return self._insufficient_result('Missing CIP code')

        try:
            cip_entry = self._cip_dataset.get(cip_code)
        except CIPNotFoundError:
            return self._insufficient_result(f'Unknown CIP code: {cip_code}')

        query = self._build_query(facts, cip_entry.description)
        retrieved_sources = self._retriever.search(query, top_k=5)
        if not self._has_sufficient_evidence(retrieved_sources):
            return self._insufficient_result('Insufficient grounded policy evidence')

        analysis_payload = self._reasoning_client.generate_structured(
            model=self._model_name,
            prompt=self._analysis_prompt_for(facts, cip_entry, retrieved_sources),
            schema=PolicyAnalysisPayload,
        )
        analysis = PolicyAnalysis(
            cip_code=cip_entry.cip_code,
            cip_title=cip_entry.title,
            summary=analysis_payload['summary'],
            evidence_strength=analysis_payload['evidence_strength'],
            retrieved_sources=retrieved_sources,
            ambiguity_notes=analysis_payload.get('ambiguity_notes', []),
        )

        verdict_payload = self._reasoning_client.generate_structured(
            model=self._model_name,
            prompt=self._verdict_prompt_for(analysis),
            schema=PolicyVerdictPayload,
        )
        source_map = {source.source_id: source for source in retrieved_sources}
        cited_sources = [source_map[source_id] for source_id in verdict_payload.get('cited_source_ids', []) if source_id in source_map]
        verdict = PolicyVerdict(
            verdict=verdict_payload['verdict'],
            confidence=verdict_payload['confidence'],
            rationale=PolicyRationale(**verdict_payload['rationale']),
            cited_sources=cited_sources,
        )
        return {
            'policy_analysis': analysis,
            'policy_verdict': verdict,
        }

    def _analysis_prompt_for(self, facts: dict[str, str], cip_entry, sources: list[RetrievedSource]) -> str:
        source_block = self._format_sources(sources)
        return (
            f"{self._analysis_prompt}\n\n"
            f"CIP CODE: {cip_entry.cip_code}\n"
            f"CIP TITLE: {cip_entry.title}\n"
            f"CIP DESCRIPTION: {cip_entry.description}\n"
            f"MAJOR: {facts.get('major', '')}\n"
            f"JOB TITLE: {facts.get('position_title', '')}\n"
            f"JOB DUTIES: {facts.get('job_duties', '')}\n\n"
            f"SOURCES:\n{source_block}\n"
        )

    def _verdict_prompt_for(self, analysis: PolicyAnalysis) -> str:
        source_block = self._format_sources(analysis.retrieved_sources)
        return (
            f"{self._verdict_prompt}\n\n"
            f"CIP CODE: {analysis.cip_code}\n"
            f"CIP TITLE: {analysis.cip_title}\n"
            f"ANALYSIS SUMMARY: {analysis.summary}\n"
            f"EVIDENCE STRENGTH: {analysis.evidence_strength}\n"
            f"AMBIGUITY NOTES: {analysis.ambiguity_notes}\n\n"
            f"SOURCES:\n{source_block}\n"
        )

    def _format_sources(self, sources: list[RetrievedSource]) -> str:
        return '\n'.join(f"- {source.source_id} | {source.citation} | {source.text}" for source in sources)

    def _build_query(self, facts: dict[str, str], cip_description: str) -> str:
        return ' '.join(
            part for part in [
                facts.get('major', ''),
                facts.get('position_title', ''),
                facts.get('job_duties', ''),
                cip_description,
                'directly related major area of study practical training',
            ] if part
        )

    def _has_sufficient_evidence(self, sources: list[RetrievedSource]) -> bool:
        source_types = {source.source_type for source in sources}
        return 'cip' in source_types and 'policy' in source_types

    def _insufficient_result(self, reason: str) -> dict[str, object]:
        rationale = PolicyRationale(
            major_match=reason,
            duty_match=reason,
            policy_basis=reason,
            summary=reason,
        )
        analysis = PolicyAnalysis(
            cip_code='',
            cip_title='',
            summary=reason,
            evidence_strength='weak',
            retrieved_sources=[],
            ambiguity_notes=[reason],
        )
        verdict = PolicyVerdict(
            verdict='insufficient_policy_evidence',
            confidence='low',
            rationale=rationale,
            cited_sources=[],
        )
        return {
            'policy_analysis': analysis,
            'policy_verdict': verdict,
        }



def evaluate_policy_state(state: dict[str, object], agent: PolicyAgent) -> dict[str, object]:
    result = agent.evaluate({k: str(v) for k, v in state.items() if isinstance(v, str)})
    updated_state = dict(state)
    updated_state["policy_analysis"] = result["policy_analysis"].model_dump()
    updated_state["policy_verdict"] = result["policy_verdict"].model_dump()
    return updated_state

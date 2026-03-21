from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RetrievedSource(BaseModel):
    source_id: str
    title: str
    citation: str
    source_type: Literal["cip", "policy"]
    text: str
    score: float = Field(ge=0.0)


class PolicyRationale(BaseModel):
    major_match: str
    duty_match: str
    policy_basis: str
    summary: str


class PolicyAnalysis(BaseModel):
    cip_code: str
    cip_title: str
    summary: str
    evidence_strength: Literal["strong", "moderate", "weak"]
    retrieved_sources: list[RetrievedSource]
    ambiguity_notes: list[str]


class PolicyVerdict(BaseModel):
    verdict: Literal[
        "directly_related",
        "not_directly_related",
        "unclear",
        "insufficient_policy_evidence",
    ]
    confidence: Literal["high", "medium", "low"]
    rationale: PolicyRationale
    cited_sources: list[RetrievedSource]

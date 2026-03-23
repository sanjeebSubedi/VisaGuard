from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class DSOCitation(BaseModel):
    title: str
    citation: str
    source_type: Literal['federal', 'university', 'cip']
    excerpt: str
    score: float = Field(ge=0.0)


class DSOResponse(BaseModel):
    answer: str
    citations: list[DSOCitation]
    confidence: Literal['high', 'medium', 'low']
    needs_human_escalation: bool
    answer_mode: Literal[
        'personalized_status',
        'general_policy',
        'school_procedure',
        'escalation_sensitive',
        'cautious_fallback',
    ]

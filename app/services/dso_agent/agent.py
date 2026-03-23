from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from typing import Literal

from app.services.dso_agent.guardrails import apply_guardrails
from app.services.dso_agent.types import DSOCitation, DSOResponse


class DSOResponsePayload(BaseModel):
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


class DSOUnavailableError(RuntimeError):
    pass


class DSOAgent:
    def __init__(self, *, reasoning_client: Any, model_name: str, synthesizer_prompt: str) -> None:
        self._reasoning_client = reasoning_client
        self._model_name = model_name
        self._synthesizer_prompt = synthesizer_prompt

    @classmethod
    def from_prompts(cls, *, reasoning_client: Any, model_name: str) -> 'DSOAgent':
        prompts_dir = Path(__file__).with_name('prompts')
        return cls(
            reasoning_client=reasoning_client,
            model_name=model_name,
            synthesizer_prompt=(prompts_dir / 'synthesizer.txt').read_text().strip(),
        )

    def synthesize(self, **kwargs) -> DSOResponse:
        return synthesize_answer(
            reasoning_client=self._reasoning_client,
            model_name=self._model_name,
            prompt_template=self._synthesizer_prompt,
            **kwargs,
        )


def synthesize_answer(
    *,
    message: str,
    mode: str,
    student_state: dict,
    retrieved_sources: list[dict],
    reasoning_client: Any,
    model_name: str,
    prompt_template: str = '',
    school_supported: bool = True,
    university_match_found: bool = True,
) -> DSOResponse:
    quoted_answer = _precomputed_time_answer(message=message, student_state=student_state)
    if quoted_answer is not None:
        return apply_guardrails(response=quoted_answer, student_state=student_state, question=message)

    fallback = _no_math_fallback(message=message, student_state=student_state)
    if fallback is not None:
        return apply_guardrails(response=fallback, student_state=student_state, question=message)

    if not retrieved_sources:
        response = DSOResponse(
            answer='I am not confident enough to answer that from the current guidance. Please rerun the workflow or contact your DSO if you need a definitive answer.',
            citations=[],
            confidence='low',
            needs_human_escalation=False,
            answer_mode='cautious_fallback',
        )
        return apply_guardrails(response=response, student_state=student_state, question=message)

    source_lines = '\n'.join(
        f"- {source['title']} | {source['citation']} | {source['excerpt']}" for source in retrieved_sources
    )
    prompt = (
        f"{prompt_template}\n\nQUESTION: {message}\nMODE: {mode}\n"
        f"STUDENT STATE: {student_state}\nSOURCES:\n{source_lines}\n"
    )
    try:
        payload = reasoning_client.generate_structured(model=model_name, prompt=prompt, schema=DSOResponsePayload)
    except Exception as exc:
        raise DSOUnavailableError(str(exc)) from exc

    try:
        response = DSOResponse.model_validate(payload)
    except Exception as exc:
        raise DSOUnavailableError('Malformed DSO response') from exc

    if not school_supported:
        response.answer = f"{response.answer} School-specific procedure guidance is unavailable for the current school record."
    elif mode == 'school_procedure' and not university_match_found:
        response.answer = f"{response.answer} School-specific steps may differ, so please confirm with your DSO."

    return apply_guardrails(response=response, student_state=student_state, question=message)


def _no_math_fallback(*, message: str, student_state: dict) -> DSOResponse | None:
    lowered = message.lower()
    if 'how many' not in lowered and 'days' not in lowered:
        return None
    if 'unemployment' not in lowered:
        return None
    clocks = ((student_state.get('timeline_status') or {}).get('clocks') or {}) if isinstance(student_state, dict) else {}
    opt_clock = clocks.get('opt_unemployment') if isinstance(clocks, dict) else None
    if isinstance(opt_clock, dict) and opt_clock.get('days_remaining') is not None:
        return None
    return DSOResponse(
        answer='I cannot safely derive that number from the current data. Please rerun the workflow or contact your DSO if you need a definitive answer.',
        citations=[],
        confidence='low',
        needs_human_escalation=False,
        answer_mode='cautious_fallback',
    )


def _precomputed_time_answer(*, message: str, student_state: dict) -> DSOResponse | None:
    lowered = message.lower()
    if 'how many' not in lowered and 'days' not in lowered:
        return None
    if 'unemployment' not in lowered:
        return None
    clocks = ((student_state.get('timeline_status') or {}).get('clocks') or {}) if isinstance(student_state, dict) else {}
    opt_clock = clocks.get('opt_unemployment') if isinstance(clocks, dict) else None
    days_remaining = opt_clock.get('days_remaining') if isinstance(opt_clock, dict) else None
    if days_remaining is None:
        return None
    return DSOResponse(
        answer=f'You have {days_remaining} days remaining on your OPT unemployment clock.',
        citations=[],
        confidence='high',
        needs_human_escalation=False,
        answer_mode='personalized_status',
    )

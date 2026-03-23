from __future__ import annotations

from app.services.dso_agent.agent import DSOAgent
from app.services.dso_agent.router import route_intent
from app.services.dso_agent.school_resolver import SchoolResolver
from app.services.dso_agent.state_loader import load_student_state


def run_state_loader_node(state: dict[str, object], *, session) -> dict[str, object]:
    student_state = load_student_state(session, str(state['user_id'])).model_dump()
    return {**state, 'student_state': student_state}


def run_intent_router_node(state: dict[str, object]) -> dict[str, object]:
    return {**state, 'intent_mode': route_intent(str(state['message']))}


def run_context_retriever_node(state: dict[str, object], *, retriever, resolver: SchoolResolver) -> dict[str, object]:
    student_state = state.get('student_state', {}) if isinstance(state.get('student_state'), dict) else {}
    school_name = student_state.get('school_name') if isinstance(student_state, dict) else None
    school_key = resolver.resolve(school_name if isinstance(school_name, str) else None)
    mode = str(state.get('intent_mode', 'personalized_status'))
    scope = 'mixed'
    if mode == 'general_policy' or mode == 'escalation_sensitive':
        scope = 'federal'
    elif mode == 'school_procedure':
        scope = 'mixed'
    results = retriever.search(str(state['message']), scope=scope, school_key=school_key)
    university_match_found = any(result.source_type == 'university' for result in results)
    return {
        **state,
        'school_supported': school_key is not None,
        'school_key': school_key,
        'university_match_found': university_match_found,
        'retrieved_sources': [result.model_dump() for result in results],
    }


def run_synthesizer_node(state: dict[str, object], *, agent: DSOAgent) -> dict[str, object]:
    response = agent.synthesize(
        message=str(state['message']),
        mode=str(state.get('intent_mode', 'personalized_status')),
        student_state=state.get('student_state', {}),
        retrieved_sources=state.get('retrieved_sources', []),
        school_supported=bool(state.get('school_supported', True)),
        university_match_found=bool(state.get('university_match_found', True)),
    )
    return {**state, **response.model_dump()}

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.dso import DSOChatRequest, DSOChatResponse
from app.core.config import Settings
from app.db.session import get_db_session
from app.graph.dso_nodes import (
    run_context_retriever_node,
    run_intent_router_node,
    run_state_loader_node,
    run_synthesizer_node,
)
from app.graph.dso_workflow import build_dso_workflow
from app.services.dso_agent.agent import DSOAgent, DSOUnavailableError
from app.services.dso_agent.retriever import HybridDSORetriever
from app.services.dso_agent.school_resolver import SchoolResolver
from app.services.dso_agent.state_loader import StudentStateNotFound, load_student_state
from app.services.reasoning_llm import GeminiReasoningClient

router = APIRouter(prefix='/api/dso', tags=['dso'])


@router.post('/chat', response_model=DSOChatResponse)
def dso_chat(payload: DSOChatRequest = Body(...), session: Session = Depends(get_db_session)) -> dict[str, object]:
    settings = Settings()
    try:
        load_student_state(session, payload.user_id)
        workflow = build_dso_chat_workflow(session=session, settings=settings)
        result = workflow.invoke(payload.model_dump())
    except StudentStateNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DSOUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail='DSO agent is temporarily unavailable. Please try again or contact your DSO.',
        ) from exc
    return {
        'answer': result['answer'],
        'citations': result['citations'],
        'confidence': result['confidence'],
        'needs_human_escalation': result['needs_human_escalation'],
        'answer_mode': result['answer_mode'],
    }


def build_dso_chat_workflow(*, session: Session, settings: Settings):
    reasoning_client = GeminiReasoningClient(api_key=settings.gemini_api_key)
    agent = DSOAgent.from_prompts(reasoning_client=reasoning_client, model_name=settings.gemini_model)
    retriever = HybridDSORetriever.load(persist_directory=Path(settings.dso_index_path))
    resolver = SchoolResolver.load(Path(settings.dso_school_aliases_path))
    return build_dso_workflow(
        state_loader_node=lambda state: run_state_loader_node(state, session=session),
        intent_router_node=run_intent_router_node,
        context_retriever_node=lambda state: run_context_retriever_node(state, retriever=retriever, resolver=resolver),
        synthesizer_node=lambda state: run_synthesizer_node(state, agent=agent),
    )

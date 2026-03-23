from pathlib import Path

from app.db.models import WorkflowResult
from app.graph.dso_nodes import (
    run_context_retriever_node,
    run_intent_router_node,
    run_state_loader_node,
    run_synthesizer_node,
)
from app.graph.dso_workflow import build_dso_workflow
from app.services.dso_agent.agent import DSOAgent
from app.services.dso_agent.indexer import build_dso_index
from app.services.dso_agent.retriever import HybridDSORetriever
from app.services.dso_agent.school_resolver import SchoolResolver


class FakeReasoningClient:
    def __init__(self, payload):
        self.payload = payload

    def generate_structured(self, *, model: str, prompt: str, schema):
        return self.payload


def test_dso_workflow_answers_personalized_status_question(db_session, tmp_path):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-22",
            timeline_status={
                "current_phase": "opt_active",
                "clocks": {
                    "opt_unemployment": {
                        "status": "active",
                        "days_remaining": 52,
                        "limit_days": 90,
                        "relevant_dates": {"card_start_date": "2026-01-01"},
                    }
                },
            },
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO", "action_plan": [], "audit_summary": "In status."},
        )
    )
    db_session.commit()

    federal_dir = tmp_path / "federal"
    federal_dir.mkdir()
    (federal_dir / "opt.md").write_text("# OPT\nStudents may work in qualifying OPT employment.")
    university_root = tmp_path / "universities"
    build_dso_index(federal_sources_dir=federal_dir, university_sources_root=university_root, persist_directory=tmp_path / "index")

    workflow = build_dso_workflow(
        state_loader_node=lambda state: run_state_loader_node(state, session=db_session),
        intent_router_node=run_intent_router_node,
        context_retriever_node=lambda state: run_context_retriever_node(
            state,
            retriever=HybridDSORetriever.load(persist_directory=tmp_path / "index"),
            resolver=SchoolResolver({"New York University": "nyu", "NYU": "nyu"}),
        ),
        synthesizer_node=lambda state: run_synthesizer_node(
            state,
            agent=DSOAgent(
                reasoning_client=FakeReasoningClient({
                    "answer": "You have 52 days remaining on your OPT unemployment clock.",
                    "citations": [],
                    "confidence": "high",
                    "needs_human_escalation": False,
                    "answer_mode": "personalized_status",
                }),
                model_name="gemini-test",
                synthesizer_prompt="prompt",
            ),
        ),
    )

    result = workflow.invoke({"user_id": "user0", "message": "How many unemployment days do I have left?", "chat_history": []})
    assert "52" in result["answer"]



def test_dso_workflow_answers_school_procedure_question_with_university_citation(db_session, tmp_path):
    db_session.add(
        WorkflowResult(
            user_id="user0",
            evaluation_date="2026-03-22",
            timeline_status={"current_phase": "opt_active", "clocks": {}},
            policy_analysis={"school_name": "New York University"},
            policy_verdict={"verdict": "directly_related"},
            final_compliance_record={"overall_state": "IN_STATUS", "severity": "INFO", "action_plan": [], "audit_summary": "In status."},
        )
    )
    db_session.commit()

    federal_dir = tmp_path / "federal"
    federal_dir.mkdir()
    (federal_dir / "travel.md").write_text("# Travel\nStudents may need a travel signature for re-entry.")
    university_dir = tmp_path / "universities" / "nyu"
    university_dir.mkdir(parents=True)
    (university_dir / "travel_signature.md").write_text("# Travel Signature\nUse the OGS portal to request your travel signature.")
    build_dso_index(federal_sources_dir=federal_dir, university_sources_root=tmp_path / "universities", persist_directory=tmp_path / "index")

    workflow = build_dso_workflow(
        state_loader_node=lambda state: run_state_loader_node(state, session=db_session),
        intent_router_node=run_intent_router_node,
        context_retriever_node=lambda state: run_context_retriever_node(
            state,
            retriever=HybridDSORetriever.load(persist_directory=tmp_path / "index"),
            resolver=SchoolResolver({"New York University": "nyu", "NYU": "nyu"}),
        ),
        synthesizer_node=lambda state: run_synthesizer_node(
            state,
            agent=DSOAgent(
                reasoning_client=FakeReasoningClient({
                    "answer": "Use the OGS portal to request your travel signature.",
                    "citations": [
                        {
                            "title": "Travel Signature",
                            "citation": "Travel Signature",
                            "source_type": "university",
                            "excerpt": "Use the OGS portal to request your travel signature.",
                            "score": 0.9,
                        }
                    ],
                    "confidence": "high",
                    "needs_human_escalation": False,
                    "answer_mode": "school_procedure",
                }),
                model_name="gemini-test",
                synthesizer_prompt="prompt",
            ),
        ),
    )

    result = workflow.invoke({"user_id": "user0", "message": "How do I get a travel signature?", "chat_history": []})
    assert result["citations"][0]["source_type"] == "university"

from app.graph.dso_workflow import build_dso_workflow


def test_dso_workflow_runs_state_loader_router_retriever_and_synthesizer():
    workflow = build_dso_workflow(
        state_loader_node=lambda state: {**state, "student_state": {"final_compliance_record": {"overall_state": "IN_STATUS", "severity": "INFO"}, "timeline_status": {}}},
        intent_router_node=lambda state: {**state, "intent_mode": "general_policy"},
        context_retriever_node=lambda state: {**state, "retrieved_sources": []},
        synthesizer_node=lambda state: {**state, "answer": "Yes", "citations": [], "confidence": "high", "needs_human_escalation": False, "answer_mode": "general_policy"},
    )
    result = workflow.invoke({"user_id": "user0", "message": "Can I work two jobs on OPT?", "chat_history": []})
    assert result["answer"] == "Yes"

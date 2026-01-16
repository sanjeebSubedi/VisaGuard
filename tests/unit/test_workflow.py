"""
Tests for LangGraph Workflow
"""

import pytest


class TestVisaGuardState:
    """Tests for the state schema."""

    def test_create_initial_state(self):
        """Should create a valid initial state."""
        from app.graph.state import create_initial_state, WorkflowStage, ComplianceVerdict
        
        state = create_initial_state(
            thread_id="thread_123",
            user_id="user_456",
        )
        
        assert state["thread_id"] == "thread_123"
        assert state["user_id"] == "user_456"
        assert state["stage"] == WorkflowStage.INTAKE
        assert state["compliance_verdict"] == ComplianceVerdict.PENDING
        assert state["document_ids"] == []
        assert state["messages"] == []

    def test_state_has_all_required_fields(self):
        """Initial state should have all required fields."""
        from app.graph.state import create_initial_state
        
        state = create_initial_state("t1", "u1")
        
        # Check key fields exist
        assert "timeline" in state
        assert "compliance_issues" in state
        assert "audit_log_ids" in state
        assert "awaiting_human_approval" in state


class TestWorkflowNodes:
    """Tests for individual workflow nodes."""

    def test_intake_node_with_documents(self):
        """Intake should route to document processing if docs present."""
        from app.graph.workflow import intake_node
        from app.graph.state import WorkflowStage
        
        state = {
            "document_ids": ["doc_1", "doc_2"],
            "messages": [],
        }
        
        result = intake_node(state)
        
        assert result["stage"] == WorkflowStage.DOCUMENT_PROCESSING

    def test_intake_node_with_policy_question(self):
        """Intake should route to policy check for policy questions."""
        from app.graph.workflow import intake_node
        from app.graph.state import WorkflowStage
        
        state = {
            "document_ids": [],
            "messages": [{"role": "user", "content": "Can I work unpaid during STEM OPT?"}],
        }
        
        result = intake_node(state)
        
        assert result["stage"] == WorkflowStage.POLICY_CHECK
        assert result["policy_query"] == "Can I work unpaid during STEM OPT?"

    def test_human_review_node(self):
        """Human review node should set awaiting flag."""
        from app.graph.workflow import human_review_node
        from app.graph.state import WorkflowStage
        
        state = {}
        
        result = human_review_node(state)
        
        assert result["awaiting_human_approval"] is True
        assert result["stage"] == WorkflowStage.HUMAN_REVIEW


class TestWorkflowRouting:
    """Tests for routing functions."""

    def test_route_after_intake_to_documents(self):
        """Should route to document processing."""
        from app.graph.workflow import route_after_intake
        from app.graph.state import WorkflowStage
        
        state = {"stage": WorkflowStage.DOCUMENT_PROCESSING}
        
        result = route_after_intake(state)
        
        assert result == "document_processing"

    def test_route_after_intake_to_policy(self):
        """Should route to policy check."""
        from app.graph.workflow import route_after_intake
        from app.graph.state import WorkflowStage
        
        state = {"stage": WorkflowStage.POLICY_CHECK}
        
        result = route_after_intake(state)
        
        assert result == "policy_check"

    def test_route_after_compliance_to_human(self):
        """Should route to human review when awaiting approval."""
        from app.graph.workflow import route_after_compliance
        
        state = {"awaiting_human_approval": True}
        
        result = route_after_compliance(state)
        
        assert result == "human_review"

    def test_route_after_compliance_to_audit(self):
        """Should route to audit when no issues."""
        from app.graph.workflow import route_after_compliance
        from app.graph.state import ComplianceVerdict
        
        state = {
            "awaiting_human_approval": False,
            "compliance_verdict": ComplianceVerdict.COMPLIANT,
        }
        
        result = route_after_compliance(state)
        
        assert result == "audit"


class TestWorkflowBuild:
    """Tests for workflow building."""

    def test_build_workflow(self):
        """Should build a valid workflow graph."""
        from app.graph.workflow import build_workflow
        
        workflow = build_workflow()
        
        # Workflow should be compiled and callable
        assert workflow is not None
        # Check that nodes were added
        assert hasattr(workflow, "invoke")

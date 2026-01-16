"""
VisaGuard LangGraph Workflow

The main orchestration graph that connects all agents and nodes:
- DocumentAgent (ingestion)
- PolicyAgent (RAG)
- TimelineManager (date calculations)
- ComplianceAgent (compliance reasoning)

Features:
- PostgresCheckpointer for state persistence
- Human-in-the-loop interrupts before critical actions
- Conditional routing based on compliance results
"""

from typing import Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.graph.state import (
    VisaGuardState,
    WorkflowStage,
    ComplianceVerdict,
    create_initial_state,
)
from app.graph.nodes.timeline_manager import timeline_manager_node
from app.graph.nodes.policy_agent import policy_agent_node
from app.graph.nodes.compliance_agent import compliance_agent_node
from app.services.audit import get_audit_service, AuditEventType


# Node: Document Intake
def intake_node(state: VisaGuardState) -> dict:
    """
    Initial node - gathers basic information about the request.
    
    In a full implementation, this would:
    - Parse user messages
    - Identify what documents are available
    - Determine what the user is asking
    """
    messages = state.get("messages", [])
    
    # If there are documents to process, move to document processing
    if state.get("document_ids"):
        return {
            **state,
            "stage": WorkflowStage.DOCUMENT_PROCESSING,
        }
    
    # Otherwise, check if there's a policy question
    if messages:
        last_message = messages[-1].get("content", "")
        if any(keyword in last_message.lower() for keyword in 
               ["can i", "is it allowed", "what are the rules", "how many days"]):
            return {
                **state,
                "stage": WorkflowStage.POLICY_CHECK,
                "policy_query": last_message,
            }
    
    # Default: stay in intake, waiting for more info
    return {
        **state,
        "stage": WorkflowStage.INTAKE,
    }


# Node: Document Processing
def document_processing_node(state: VisaGuardState) -> dict:
    """
    Process uploaded documents to extract structured data.
    
    In production, this would call the IngestionService and DocumentAgent
    to extract student/employer data from uploaded documents.
    """
    # For now, just mark as processed and move to timeline check
    # In production: call ingestion service, extract fields
    
    return {
        **state,
        "stage": WorkflowStage.TIMELINE_CHECK,
    }


# Node: Audit Logging Wrapper
def audit_compliance_node(state: VisaGuardState) -> dict:
    """
    Wrapper that logs compliance checks to the audit service.
    """
    audit_service = get_audit_service()
    
    # Log the compliance check
    entry_id = audit_service.log_event(
        thread_id=state.get("thread_id", "unknown"),
        user_id=state.get("user_id", "unknown"),
        event_type=AuditEventType.COMPLIANCE_CHECK,
        inputs={
            "document_ids": state.get("document_ids", []),
            "opt_type": state.get("opt_type", "unknown"),
            "unemployment_days": state.get("cumulative_unemployment_days", 0),
        },
        outputs={
            "verdict": state.get("compliance_verdict", ComplianceVerdict.PENDING).value,
            "issues_count": len(state.get("compliance_issues", [])),
        },
    )
    
    # Add audit entry ID to state
    audit_ids = state.get("audit_log_ids", [])
    audit_ids.append(entry_id)
    
    return {
        **state,
        "audit_log_ids": audit_ids,
    }


# Node: Human Review Handler
def human_review_node(state: VisaGuardState) -> dict:
    """
    Handler for human-in-the-loop review.
    
    This node is entered when:
    - Compliance check has low confidence
    - Before generating official forms
    
    The graph execution will be interrupted here, waiting for human input.
    """
    return {
        **state,
        "awaiting_human_approval": True,
        "stage": WorkflowStage.HUMAN_REVIEW,
    }


# Node: Complete
def complete_node(state: VisaGuardState) -> dict:
    """
    Terminal node for successful completion.
    """
    return {
        **state,
        "stage": WorkflowStage.COMPLETE,
        "awaiting_human_approval": False,
    }


# Node: Error Handler
def error_node(state: VisaGuardState) -> dict:
    """
    Terminal node for error states.
    """
    return {
        **state,
        "stage": WorkflowStage.ERROR,
    }


# Routing Functions
def route_after_intake(state: VisaGuardState) -> Literal["document_processing", "policy_check", "intake"]:
    """Route after intake based on available data."""
    stage = state.get("stage", WorkflowStage.INTAKE)
    
    if stage == WorkflowStage.DOCUMENT_PROCESSING:
        return "document_processing"
    elif stage == WorkflowStage.POLICY_CHECK:
        return "policy_check"
    else:
        return "intake"


def route_after_timeline(state: VisaGuardState) -> Literal["compliance_check", "error"]:
    """Route after timeline calculations."""
    timeline = state.get("timeline", {})
    
    # Check for critical timeline issues that need immediate attention
    if timeline.get("warning_level") == "violation":
        # Still go to compliance check to document the violation
        pass
    
    if state.get("stage") == WorkflowStage.ERROR:
        return "error"
    
    return "compliance_check"


def route_after_compliance(state: VisaGuardState) -> Literal["human_review", "audit", "complete"]:
    """Route after compliance check based on verdict and confidence."""
    verdict = state.get("compliance_verdict", ComplianceVerdict.PENDING)
    awaiting_approval = state.get("awaiting_human_approval", False)
    
    if awaiting_approval:
        return "human_review"
    
    if verdict in [ComplianceVerdict.VIOLATION, ComplianceVerdict.NEEDS_REVIEW]:
        return "human_review"
    
    return "audit"


def route_after_human_review(state: VisaGuardState) -> Literal["audit", "complete"]:
    """Route after human review."""
    feedback = state.get("human_feedback")
    
    if feedback:
        return "audit"
    
    # If still awaiting feedback, stay (will interrupt)
    return "audit"


def build_workflow(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_before: Optional[list[str]] = None,
) -> StateGraph:
    """
    Build the VisaGuard LangGraph workflow.
    
    Args:
        checkpointer: Optional checkpoint saver for state persistence.
        interrupt_before: Nodes to interrupt before (for HITL).
        
    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create the graph
    workflow = StateGraph(VisaGuardState)
    
    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("document_processing", document_processing_node)
    workflow.add_node("policy_check", policy_agent_node)
    workflow.add_node("timeline_check", timeline_manager_node)
    workflow.add_node("compliance_check", compliance_agent_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("audit", audit_compliance_node)
    workflow.add_node("complete", complete_node)
    workflow.add_node("error", error_node)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "document_processing": "document_processing",
            "policy_check": "policy_check",
            "intake": END,  # Wait for more input
        }
    )
    
    # Document processing leads to timeline check
    workflow.add_edge("document_processing", "timeline_check")
    
    # Policy check can lead to compliance or back to intake
    workflow.add_edge("policy_check", "compliance_check")
    
    # Timeline check leads to compliance
    workflow.add_conditional_edges(
        "timeline_check",
        route_after_timeline,
        {
            "compliance_check": "compliance_check",
            "error": "error",
        }
    )
    
    # Compliance check with conditional routing
    workflow.add_conditional_edges(
        "compliance_check",
        route_after_compliance,
        {
            "human_review": "human_review",
            "audit": "audit",
            "complete": "complete",
        }
    )
    
    # Human review leads to audit
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "audit": "audit",
            "complete": "complete",
        }
    )
    
    # Audit leads to complete
    workflow.add_edge("audit", "complete")
    
    # Terminal nodes
    workflow.add_edge("complete", END)
    workflow.add_edge("error", END)
    
    # Compile with optional checkpointer and interrupts
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before:
        compile_kwargs["interrupt_before"] = interrupt_before
    
    return workflow.compile(**compile_kwargs)


def get_workflow(
    with_persistence: bool = False,
    with_hitl: bool = True,
) -> StateGraph:
    """
    Get a configured workflow instance.
    
    Args:
        with_persistence: Whether to use Postgres checkpointing.
        with_hitl: Whether to enable human-in-the-loop interrupts.
        
    Returns:
        Compiled workflow.
    """
    checkpointer = None
    interrupt_before = None
    
    if with_persistence:
        # In production, this would use PostgresCheckpointer
        # from langgraph.checkpoint.postgres import PostgresSaver
        # checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
        pass
    
    if with_hitl:
        # Interrupt before human review node
        interrupt_before = ["human_review"]
    
    return build_workflow(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
    )


# Convenience function for running the workflow
async def run_compliance_check(
    user_id: str,
    thread_id: str,
    opt_type: str = "post_completion",
    opt_start_date: Optional[str] = None,
    opt_end_date: Optional[str] = None,
    document_ids: Optional[list[str]] = None,
    user_message: Optional[str] = None,
) -> VisaGuardState:
    """
    Run a compliance check through the workflow.
    
    This is the main entry point for triggering compliance analysis.
    
    Returns:
        Final workflow state with compliance results.
    """
    # Create initial state
    state = create_initial_state(thread_id, user_id)
    
    # Update with provided data
    state["opt_type"] = opt_type
    if opt_start_date:
        state["opt_start_date"] = opt_start_date
    if opt_end_date:
        state["opt_end_date"] = opt_end_date
    if document_ids:
        state["document_ids"] = document_ids
    if user_message:
        state["messages"] = [{"role": "user", "content": user_message}]
    
    # Get workflow
    workflow = get_workflow(with_persistence=False, with_hitl=False)
    
    # Run workflow
    result = await workflow.ainvoke(state)
    
    return result

"""
LangGraph State Schema

Defines the state object that flows through the VisaGuard workflow.

Key design principle: State contains REFERENCES (IDs), not data.
- Document content is stored in Postgres/Cache
- State only carries document_id, user_id, etc.
- This prevents state bloat and reduces checkpoint size

The state is checkpointed after each node execution using PostgresCheckpointer.
"""

from typing import Annotated, Optional, TypedDict
from datetime import date
from enum import Enum


class WorkflowStage(str, Enum):
    """Current stage in the compliance workflow."""
    INTAKE = "intake"
    DOCUMENT_PROCESSING = "document_processing"
    POLICY_CHECK = "policy_check"
    TIMELINE_CHECK = "timeline_check"
    COMPLIANCE_REVIEW = "compliance_review"
    HUMAN_REVIEW = "human_review"
    FORM_GENERATION = "form_generation"
    COMPLETE = "complete"
    ERROR = "error"


class ComplianceVerdict(str, Enum):
    """Possible compliance outcomes."""
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"
    PENDING = "pending"


class VisaGuardState(TypedDict, total=False):
    """
    The main state object for the VisaGuard LangGraph workflow.
    
    IMPORTANT: This state is persisted to Postgres via checkpointing.
    Only store IDs and computed values - NOT raw document content.
    
    Attributes:
        # Identity & Session
        thread_id: Unique conversation thread ID
        user_id: Reference to user in the users table
        session_start: When this session started
        
        # Workflow Control
        stage: Current stage in the workflow
        error_message: Error details if stage == ERROR
        
        # Document References (IDs only, not content)
        document_ids: List of document IDs being processed
        active_document_id: Currently active document
        
        # Student Information (extracted data - stored separately, referenced here)
        student_data_id: Reference to extracted student data in secure storage
        
        # Employer Information
        employer_data_id: Reference to employer data in secure storage
        
        # Timeline State (computed by TimelineManager)
        timeline: Computed timeline values (unemployment days, warnings, etc.)
        
        # Policy Query Results
        policy_query: Current policy question being researched
        policy_result: Results from PolicyAgent
        
        # Compliance Results
        compliance_verdict: Final compliance determination
        compliance_issues: List of identified issues
        compliance_citations: Regulatory citations supporting the verdict
        
        # Form Generation (Phase 5)
        form_data_id: Reference to form data ready for PDF generation
        generated_form_path: Path to generated PDF
        
        # Audit Trail
        audit_log_ids: References to audit log entries
        
        # Human-in-the-Loop
        awaiting_human_approval: Whether we're paused for human review
        human_approval_type: What type of approval is needed
        human_feedback: Feedback from human reviewer
    """
    
    # Identity & Session
    thread_id: str
    user_id: str
    session_start: str  # ISO format date string
    
    # Workflow Control
    stage: WorkflowStage
    error_message: Optional[str]
    
    # Document References (IDs only)
    document_ids: list[str]
    active_document_id: Optional[str]
    
    # Student Data Reference
    student_data_id: Optional[str]
    
    # Employer Data Reference
    employer_data_id: Optional[str]
    
    # OPT Details (needed for timeline calculations)
    opt_type: str  # "post_completion" or "stem_extension"
    opt_start_date: Optional[str]
    opt_end_date: Optional[str]
    
    # Employment Status
    is_currently_employed: bool
    last_employment_end_date: Optional[str]
    cumulative_unemployment_days: int
    
    # Timeline (computed)
    timeline: Optional[dict]
    
    # Policy Query
    policy_query: Optional[str]
    policy_result: Optional[dict]
    
    # Compliance Results
    compliance_verdict: ComplianceVerdict
    compliance_issues: list[dict]
    compliance_citations: list[dict]
    
    # Form Generation
    form_data_id: Optional[str]
    generated_form_path: Optional[str]
    
    # Audit Trail
    audit_log_ids: list[str]
    
    # Human-in-the-Loop
    awaiting_human_approval: bool
    human_approval_type: Optional[str]
    human_feedback: Optional[str]
    
    # Messages (for conversational interface)
    messages: list[dict]  # {"role": "user"|"assistant", "content": "..."}


def create_initial_state(
    thread_id: str,
    user_id: str,
) -> VisaGuardState:
    """
    Create a new initial state for a VisaGuard workflow session.
    
    Args:
        thread_id: Unique identifier for this conversation thread.
        user_id: User ID from the users table.
        
    Returns:
        A fresh VisaGuardState with default values.
    """
    from datetime import datetime
    
    return VisaGuardState(
        # Identity
        thread_id=thread_id,
        user_id=user_id,
        session_start=datetime.now().isoformat(),
        
        # Workflow
        stage=WorkflowStage.INTAKE,
        error_message=None,
        
        # Documents
        document_ids=[],
        active_document_id=None,
        
        # Data References
        student_data_id=None,
        employer_data_id=None,
        
        # OPT Details
        opt_type="post_completion",
        opt_start_date=None,
        opt_end_date=None,
        
        # Employment
        is_currently_employed=False,
        last_employment_end_date=None,
        cumulative_unemployment_days=0,
        
        # Computed
        timeline=None,
        
        # Policy
        policy_query=None,
        policy_result=None,
        
        # Compliance
        compliance_verdict=ComplianceVerdict.PENDING,
        compliance_issues=[],
        compliance_citations=[],
        
        # Forms
        form_data_id=None,
        generated_form_path=None,
        
        # Audit
        audit_log_ids=[],
        
        # HITL
        awaiting_human_approval=False,
        human_approval_type=None,
        human_feedback=None,
        
        # Messages
        messages=[],
    )

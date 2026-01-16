"""
DSO Agent - Form Generation with Human-in-the-Loop

This agent generates the I-983 Training Plan form by:
1. Gathering all required data from state
2. Validating the data is complete
3. Presenting a preview for human approval (HITL)
4. Generating the final PDF

CRITICAL: This node is ALWAYS interrupted before execution.
The human must approve the form data before generation.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from app.graph.state import VisaGuardState, WorkflowStage, ComplianceVerdict
from app.services.form_filler import FormFiller, get_form_filler
from app.services.audit import get_audit_service, AuditEventType


@dataclass
class FormPreview:
    """Preview of form data for human review."""
    form_type: str
    student_summary: str
    employer_summary: str
    training_plan_summary: str
    is_complete: bool
    missing_fields: list[str]
    warnings: list[str]


@dataclass
class FormGenerationResult:
    """Result of form generation."""
    success: bool
    output_path: Optional[str]
    error_message: Optional[str]
    preview: Optional[FormPreview]


class DSOAgent:
    """
    Agent responsible for generating official forms.
    
    This agent:
    1. Validates all required data is present
    2. Creates a preview for human approval
    3. Generates the PDF after approval
    
    Usage:
        agent = DSOAgent()
        preview = agent.create_preview(student_data, employer_data, training_plan)
        if approved:
            result = agent.generate_form(student_data, employer_data, training_plan)
    """
    
    REQUIRED_STUDENT_FIELDS = [
        "first_name", "last_name", "sevis_id", "email",
        "school_name", "degree_level", "graduation_date", "major_cip",
    ]
    
    REQUIRED_EMPLOYER_FIELDS = [
        "company_name", "street", "city", "state", "zip", "ein",
    ]
    
    REQUIRED_TRAINING_PLAN_FIELDS = [
        "start_date", "hours_per_week", "salary",
        "goals", "role_description", "oversight",
        "supervisor_name", "supervisor_email",
    ]
    
    def __init__(self):
        """Initialize the DSO Agent."""
        self.form_filler = get_form_filler()
        self.audit_service = get_audit_service()
    
    def validate_data(
        self,
        student_data: dict,
        employer_data: dict,
        training_plan: dict,
    ) -> tuple[bool, list[str]]:
        """
        Validate that all required data is present.
        
        Returns:
            Tuple of (is_valid, list_of_missing_fields).
        """
        missing = []
        
        for field in self.REQUIRED_STUDENT_FIELDS:
            if not student_data.get(field):
                missing.append(f"Student: {field}")
        
        for field in self.REQUIRED_EMPLOYER_FIELDS:
            if not employer_data.get(field):
                missing.append(f"Employer: {field}")
        
        for field in self.REQUIRED_TRAINING_PLAN_FIELDS:
            if not training_plan.get(field):
                missing.append(f"Training Plan: {field}")
        
        return len(missing) == 0, missing
    
    def generate_warnings(
        self,
        student_data: dict,
        employer_data: dict,
        training_plan: dict,
    ) -> list[str]:
        """
        Generate warnings about potential issues with the form data.
        
        Returns:
            List of warning messages.
        """
        warnings = []
        
        # Check hours
        hours = training_plan.get("hours_per_week", 0)
        try:
            hours = int(hours)
            if hours < 20:
                warnings.append(
                    f"Hours per week ({hours}) is below the minimum required 20 hours."
                )
        except (ValueError, TypeError):
            warnings.append("Hours per week is not a valid number.")
        
        # Check E-Verify
        if not employer_data.get("e_verify_id"):
            warnings.append(
                "E-Verify Company ID not provided. STEM OPT requires E-Verify enrollment."
            )
        
        # Check goals length
        goals = training_plan.get("goals", "")
        if len(goals) < 100:
            warnings.append(
                "Goals and Objectives description seems short. "
                "Consider providing more detail about learning objectives."
            )
        
        # Check role description
        role = training_plan.get("role_description", "")
        if len(role) < 100:
            warnings.append(
                "Role description seems short. "
                "Consider elaborating on how the role relates to the STEM degree."
            )
        
        return warnings
    
    def create_preview(
        self,
        student_data: dict,
        employer_data: dict,
        training_plan: dict,
    ) -> FormPreview:
        """
        Create a preview of the form for human review.
        
        This is displayed to the user BEFORE form generation.
        
        Returns:
            FormPreview object with summary and validation results.
        """
        is_complete, missing = self.validate_data(
            student_data, employer_data, training_plan
        )
        warnings = self.generate_warnings(
            student_data, employer_data, training_plan
        )
        
        student_summary = (
            f"**Student:** {student_data.get('first_name', '?')} "
            f"{student_data.get('last_name', '?')}\n"
            f"SEVIS ID: {student_data.get('sevis_id', 'N/A')}\n"
            f"School: {student_data.get('school_name', 'N/A')}\n"
            f"Major: {student_data.get('major_cip', 'N/A')}"
        )
        
        employer_summary = (
            f"**Employer:** {employer_data.get('company_name', '?')}\n"
            f"Location: {employer_data.get('city', '?')}, "
            f"{employer_data.get('state', '?')}\n"
            f"EIN: {employer_data.get('ein', 'N/A')}"
        )
        
        training_summary = (
            f"**Training Plan:**\n"
            f"Start Date: {training_plan.get('start_date', 'N/A')}\n"
            f"Hours/Week: {training_plan.get('hours_per_week', 'N/A')}\n"
            f"Salary: {training_plan.get('salary', 'N/A')}\n"
            f"Supervisor: {training_plan.get('supervisor_name', 'N/A')}"
        )
        
        return FormPreview(
            form_type="I-983 Training Plan",
            student_summary=student_summary,
            employer_summary=employer_summary,
            training_plan_summary=training_summary,
            is_complete=is_complete,
            missing_fields=missing,
            warnings=warnings,
        )
    
    def generate_form(
        self,
        student_data: dict,
        employer_data: dict,
        training_plan: dict,
        thread_id: str = "unknown",
        user_id: str = "unknown",
    ) -> FormGenerationResult:
        """
        Generate the I-983 PDF form.
        
        This should only be called AFTER human approval.
        
        Returns:
            FormGenerationResult with success status and output path.
        """
        # Validate first
        is_valid, missing = self.validate_data(
            student_data, employer_data, training_plan
        )
        
        if not is_valid:
            return FormGenerationResult(
                success=False,
                output_path=None,
                error_message=f"Cannot generate form. Missing fields: {', '.join(missing)}",
                preview=None,
            )
        
        try:
            # Generate the form
            output_path = self.form_filler.fill_i983(
                student_data=student_data,
                employer_data=employer_data,
                training_plan=training_plan,
            )
            
            # Log to audit
            self.audit_service.log_event(
                thread_id=thread_id,
                user_id=user_id,
                event_type=AuditEventType.FORM_GENERATED,
                inputs={
                    "form_type": "I-983",
                    "student_sevis": student_data.get("sevis_id", "[REDACTED]"),
                    "employer": employer_data.get("company_name", "Unknown"),
                },
                outputs={
                    "output_path": str(output_path),
                    "success": True,
                },
            )
            
            return FormGenerationResult(
                success=True,
                output_path=str(output_path),
                error_message=None,
                preview=self.create_preview(student_data, employer_data, training_plan),
            )
        
        except Exception as e:
            self.audit_service.log_event(
                thread_id=thread_id,
                user_id=user_id,
                event_type=AuditEventType.ERROR,
                inputs={"form_type": "I-983"},
                outputs={"error": str(e)},
            )
            
            return FormGenerationResult(
                success=False,
                output_path=None,
                error_message=f"Form generation failed: {str(e)}",
                preview=None,
            )


def dso_agent_node(state: VisaGuardState) -> dict:
    """
    LangGraph node wrapper for DSO Agent.
    
    This node is interrupted BEFORE execution to allow human review.
    
    Flow:
    1. First entry: Create preview, set awaiting_human_approval
    2. After approval: Generate form
    """
    agent = DSOAgent()
    
    # Check if we're awaiting approval
    if state.get("awaiting_human_approval") and state.get("human_approval_type") == "form_generation":
        # Check if we have EXPLICIT approval
        feedback = state.get("human_feedback", "")
        
        # SAFETY: Silence does NOT mean consent for federal documents
        # Require explicit approval keywords
        is_approved = (
            "approve" in feedback.lower() or
            "yes" in feedback.lower() or
            "generate" in feedback.lower() or
            "confirm" in feedback.lower()
        )
        
        if is_approved:
            # Generate the form
            # In production, these would be fetched from secure storage
            student_data = state.get("student_data", {})
            employer_data = state.get("employer_data", {})
            training_plan = state.get("training_plan", {})
            
            result = agent.generate_form(
                student_data=student_data,
                employer_data=employer_data,
                training_plan=training_plan,
                thread_id=state.get("thread_id", "unknown"),
                user_id=state.get("user_id", "unknown"),
            )
            
            if result.success:
                return {
                    **state,
                    "stage": WorkflowStage.COMPLETE,
                    "generated_form_path": result.output_path,
                    "awaiting_human_approval": False,
                    "messages": state.get("messages", []) + [{
                        "role": "assistant",
                        "content": f"✅ Form generated successfully: {result.output_path}"
                    }],
                }
            else:
                return {
                    **state,
                    "stage": WorkflowStage.ERROR,
                    "error_message": result.error_message,
                    "awaiting_human_approval": False,
                }
        else:
            # Not explicitly approved - pause and ask for explicit confirmation
            # This handles empty feedback, rejections, and unclear responses
            return {
                **state,
                "awaiting_human_approval": False,
                "messages": state.get("messages", []) + [{
                    "role": "assistant",
                    "content": (
                        "❌ Form generation paused. "
                        "Please type **'Approve'** or **'Yes'** to proceed, "
                        "or provide feedback to make changes."
                    )
                }],
            }
    
    # First entry: Create preview
    student_data = state.get("student_data", {})
    employer_data = state.get("employer_data", {})
    training_plan = state.get("training_plan", {})
    
    preview = agent.create_preview(
        student_data=student_data,
        employer_data=employer_data,
        training_plan=training_plan,
    )
    
    # Build preview message
    preview_message = f"""
## Form Preview: {preview.form_type}

{preview.student_summary}

{preview.employer_summary}

{preview.training_plan_summary}

### Validation Status
- **Complete:** {'✅ Yes' if preview.is_complete else '❌ No'}
"""
    
    if preview.missing_fields:
        preview_message += "\n**Missing Fields:**\n"
        for field in preview.missing_fields:
            preview_message += f"- {field}\n"
    
    if preview.warnings:
        preview_message += "\n**Warnings:**\n"
        for warning in preview.warnings:
            preview_message += f"- ⚠️ {warning}\n"
    
    preview_message += "\n**Please review and approve to generate the form.**"
    
    return {
        **state,
        "stage": WorkflowStage.FORM_GENERATION,
        "awaiting_human_approval": True,
        "human_approval_type": "form_generation",
        "messages": state.get("messages", []) + [{
            "role": "assistant",
            "content": preview_message,
        }],
    }

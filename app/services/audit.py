"""
Audit Service - Decision Logging and Explanation Store

Stores the reasoning trace for every compliance verdict for:
- Trust: Users can see why a decision was made
- Debugging: Engineers can trace issues
- Legal: Maintains record of compliance determinations

Each audit entry includes:
- Inputs (what data was used)
- Retrieved regulations (what policies were referenced)
- Timeline values (what calculations were done)
- Final verdict (the decision)
- Reasoning trace (why that decision was made)
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from enum import Enum
import json
import hashlib
from pathlib import Path

from app.core.config import DATA_DIR


class AuditEventType(str, Enum):
    """Types of auditable events."""
    DOCUMENT_INGESTED = "document_ingested"
    POLICY_QUERIED = "policy_queried"
    TIMELINE_CALCULATED = "timeline_calculated"
    COMPLIANCE_CHECK = "compliance_check"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_REVIEW_COMPLETED = "human_review_completed"
    FORM_GENERATED = "form_generated"
    ERROR = "error"


@dataclass
class AuditEntry:
    """A single audit log entry."""
    entry_id: str
    thread_id: str
    user_id: str
    event_type: AuditEventType
    timestamp: str  # ISO format
    
    # Event-specific data
    inputs: dict  # What data was used (scrubbed of PII)
    outputs: dict  # What was produced
    
    # For compliance checks
    verdict: Optional[str] = None
    issues: Optional[list] = None
    citations: Optional[list] = None
    reasoning_trace: Optional[str] = None
    
    # Metadata
    model_used: Optional[str] = None
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None


class AuditService:
    """
    Service for logging and retrieving audit entries.
    
    In production, this would write to a Postgres table.
    For MVP, it writes to a JSON file.
    
    Usage:
        service = AuditService()
        entry_id = service.log_compliance_check(
            thread_id="...",
            user_id="...",
            inputs={...},
            outputs={...},
            verdict="COMPLIANT",
            ...
        )
        
        # Later, retrieve the audit trail
        entries = service.get_thread_audit_trail(thread_id)
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize the Audit Service.
        
        Args:
            storage_path: Path for storing audit logs (file-based for MVP).
        """
        self.storage_path = storage_path or (DATA_DIR / ".audit" / "logs.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _generate_entry_id(self, thread_id: str, event_type: str) -> str:
        """Generate a unique entry ID."""
        timestamp = datetime.now().isoformat()
        data = f"{thread_id}:{event_type}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _append_entry(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log file."""
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
    
    def log_event(
        self,
        thread_id: str,
        user_id: str,
        event_type: AuditEventType,
        inputs: dict,
        outputs: dict,
        **kwargs,
    ) -> str:
        """
        Log a generic audit event.
        
        Returns:
            The generated entry ID.
        """
        entry = AuditEntry(
            entry_id=self._generate_entry_id(thread_id, event_type.value),
            thread_id=thread_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            inputs=inputs,
            outputs=outputs,
            **kwargs,
        )
        self._append_entry(entry)
        return entry.entry_id
    
    def log_compliance_check(
        self,
        thread_id: str,
        user_id: str,
        inputs: dict,
        verdict: str,
        issues: list,
        citations: list,
        reasoning_trace: str,
        confidence: float,
        model_used: str = "gpt-4o-mini",
        duration_ms: int = 0,
    ) -> str:
        """
        Log a compliance check event with full reasoning trace.
        
        This is the primary audit entry for compliance decisions.
        
        Returns:
            The generated entry ID.
        """
        entry = AuditEntry(
            entry_id=self._generate_entry_id(thread_id, "compliance_check"),
            thread_id=thread_id,
            user_id=user_id,
            event_type=AuditEventType.COMPLIANCE_CHECK,
            timestamp=datetime.now().isoformat(),
            inputs=self._scrub_inputs(inputs),
            outputs={"verdict": verdict, "issue_count": len(issues)},
            verdict=verdict,
            issues=issues,
            citations=citations,
            reasoning_trace=reasoning_trace,
            model_used=model_used,
            confidence=confidence,
            duration_ms=duration_ms,
        )
        self._append_entry(entry)
        return entry.entry_id
    
    def log_human_review(
        self,
        thread_id: str,
        user_id: str,
        review_type: str,
        original_verdict: str,
        human_decision: str,
        human_notes: str,
    ) -> str:
        """
        Log a human review event.
        
        Returns:
            The generated entry ID.
        """
        entry = AuditEntry(
            entry_id=self._generate_entry_id(thread_id, "human_review"),
            thread_id=thread_id,
            user_id=user_id,
            event_type=AuditEventType.HUMAN_REVIEW_COMPLETED,
            timestamp=datetime.now().isoformat(),
            inputs={
                "review_type": review_type,
                "original_verdict": original_verdict,
            },
            outputs={
                "human_decision": human_decision,
                "human_notes": human_notes,
            },
        )
        self._append_entry(entry)
        return entry.entry_id
    
    def _scrub_inputs(self, inputs: dict) -> dict:
        """
        Ensure no raw PII is logged.
        
        This is a safety measure - inputs should already be scrubbed,
        but we double-check here.
        """
        scrubbed = {}
        for key, value in inputs.items():
            if key in ["raw_text", "student_name", "ssn", "sevis_id", "email", "phone"]:
                scrubbed[key] = "[REDACTED]"
            elif isinstance(value, dict):
                scrubbed[key] = self._scrub_inputs(value)
            else:
                scrubbed[key] = value
        return scrubbed
    
    def get_thread_audit_trail(
        self,
        thread_id: str,
    ) -> list[AuditEntry]:
        """
        Retrieve all audit entries for a given thread.
        
        Returns:
            List of AuditEntry objects in chronological order.
        """
        entries = []
        
        if not self.storage_path.exists():
            return entries
        
        with open(self.storage_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("thread_id") == thread_id:
                    entries.append(AuditEntry(
                        entry_id=data["entry_id"],
                        thread_id=data["thread_id"],
                        user_id=data["user_id"],
                        event_type=AuditEventType(data["event_type"]),
                        timestamp=data["timestamp"],
                        inputs=data.get("inputs", {}),
                        outputs=data.get("outputs", {}),
                        verdict=data.get("verdict"),
                        issues=data.get("issues"),
                        citations=data.get("citations"),
                        reasoning_trace=data.get("reasoning_trace"),
                        model_used=data.get("model_used"),
                        confidence=data.get("confidence"),
                        duration_ms=data.get("duration_ms"),
                    ))
        
        return sorted(entries, key=lambda e: e.timestamp)
    
    def get_compliance_explanation(
        self,
        thread_id: str,
    ) -> Optional[dict]:
        """
        Get a human-readable explanation of the latest compliance decision.
        
        This is what we show to the user when they ask "why did you say that?"
        
        Returns:
            Dict with verdict, issues, and reasoning, or None if no check found.
        """
        entries = self.get_thread_audit_trail(thread_id)
        
        # Find the most recent compliance check
        for entry in reversed(entries):
            if entry.event_type == AuditEventType.COMPLIANCE_CHECK:
                return {
                    "timestamp": entry.timestamp,
                    "verdict": entry.verdict,
                    "issues": entry.issues or [],
                    "citations": entry.citations or [],
                    "reasoning": entry.reasoning_trace,
                    "confidence": entry.confidence,
                    "was_reviewed_by_human": any(
                        e.event_type == AuditEventType.HUMAN_REVIEW_COMPLETED
                        for e in entries
                        if e.timestamp > entry.timestamp
                    ),
                }
        
        return None


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service

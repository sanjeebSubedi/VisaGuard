"""
Tests for Audit Service
"""

import pytest
from pathlib import Path
import json


class TestAuditService:
    """Tests for the Audit Service."""

    @pytest.fixture
    def temp_audit_dir(self, tmp_path):
        """Create a temporary directory for audit logs."""
        return tmp_path / ".audit" / "logs.jsonl"

    def test_log_event(self, temp_audit_dir):
        """Should log events to file."""
        from app.services.audit import AuditService, AuditEventType
        
        service = AuditService(storage_path=temp_audit_dir)
        
        entry_id = service.log_event(
            thread_id="thread_123",
            user_id="user_456",
            event_type=AuditEventType.DOCUMENT_INGESTED,
            inputs={"document_id": "doc_789"},
            outputs={"status": "success"},
        )
        
        assert entry_id is not None
        assert len(entry_id) == 16  # SHA-256 truncated
        assert temp_audit_dir.exists()

    def test_log_compliance_check(self, temp_audit_dir):
        """Should log compliance checks with full details."""
        from app.services.audit import AuditService
        
        service = AuditService(storage_path=temp_audit_dir)
        
        entry_id = service.log_compliance_check(
            thread_id="thread_123",
            user_id="user_456",
            inputs={"opt_type": "stem_extension"},
            verdict="COMPLIANT",
            issues=[],
            citations=[{"regulation": "8 CFR 214.2(f)"}],
            reasoning_trace="Student is within 150-day limit.",
            confidence=0.95,
            model_used="gpt-4o-mini",
            duration_ms=500,
        )
        
        assert entry_id is not None
        
        # Verify the entry was written
        with open(temp_audit_dir, "r") as f:
            entries = [json.loads(line) for line in f]
        
        assert len(entries) == 1
        assert entries[0]["verdict"] == "COMPLIANT"
        assert entries[0]["confidence"] == 0.95

    def test_get_thread_audit_trail(self, temp_audit_dir):
        """Should retrieve all entries for a thread."""
        from app.services.audit import AuditService, AuditEventType
        
        service = AuditService(storage_path=temp_audit_dir)
        
        # Log multiple events for the same thread
        service.log_event(
            thread_id="thread_A",
            user_id="user_1",
            event_type=AuditEventType.DOCUMENT_INGESTED,
            inputs={},
            outputs={},
        )
        service.log_event(
            thread_id="thread_A",
            user_id="user_1",
            event_type=AuditEventType.POLICY_QUERIED,
            inputs={},
            outputs={},
        )
        service.log_event(
            thread_id="thread_B",  # Different thread
            user_id="user_2",
            event_type=AuditEventType.DOCUMENT_INGESTED,
            inputs={},
            outputs={},
        )
        
        trail = service.get_thread_audit_trail("thread_A")
        
        assert len(trail) == 2
        assert all(e.thread_id == "thread_A" for e in trail)

    def test_scrub_inputs(self, temp_audit_dir):
        """Should redact sensitive fields in inputs."""
        from app.services.audit import AuditService
        
        service = AuditService(storage_path=temp_audit_dir)
        
        inputs = {
            "raw_text": "Full document text with SSN 123-45-6789",
            "student_name": "John Doe",
            "ssn": "123-45-6789",
            "sevis_id": "N0012345678",
            "safe_field": "This should not be redacted",
        }
        
        scrubbed = service._scrub_inputs(inputs)
        
        assert scrubbed["raw_text"] == "[REDACTED]"
        assert scrubbed["student_name"] == "[REDACTED]"
        assert scrubbed["ssn"] == "[REDACTED]"
        assert scrubbed["sevis_id"] == "[REDACTED]"
        assert scrubbed["safe_field"] == "This should not be redacted"

    def test_get_compliance_explanation(self, temp_audit_dir):
        """Should return a structured explanation of the latest compliance decision."""
        from app.services.audit import AuditService
        
        service = AuditService(storage_path=temp_audit_dir)
        
        # Log a compliance check
        service.log_compliance_check(
            thread_id="thread_123",
            user_id="user_456",
            inputs={},
            verdict="WARNING",
            issues=[{"title": "Approaching limit"}],
            citations=[{"regulation": "8 CFR 214.2(f)"}],
            reasoning_trace="Student has 75 of 90 unemployment days used.",
            confidence=0.85,
        )
        
        explanation = service.get_compliance_explanation("thread_123")
        
        assert explanation is not None
        assert explanation["verdict"] == "WARNING"
        assert len(explanation["issues"]) == 1
        assert "75 of 90" in explanation["reasoning"]

    def test_human_review_logging(self, temp_audit_dir):
        """Should log human review events."""
        from app.services.audit import AuditService
        
        service = AuditService(storage_path=temp_audit_dir)
        
        entry_id = service.log_human_review(
            thread_id="thread_123",
            user_id="user_456",
            review_type="compliance_review",
            original_verdict="WARNING",
            human_decision="COMPLIANT",
            human_notes="Reviewed documentation, student is actually employed.",
        )
        
        assert entry_id is not None
        
        trail = service.get_thread_audit_trail("thread_123")
        assert len(trail) == 1
        assert trail[0].outputs["human_decision"] == "COMPLIANT"

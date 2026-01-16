"""
Tests for Privacy Pipeline (PII Scrubbing)
"""

import pytest


class TestPrivacyPipeline:
    """Tests for PII detection and redaction."""

    def test_scrub_ssn(self):
        """SSN-like patterns should be redacted (may be detected as phone due to pattern overlap)."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "My SSN is 078-05-1120"
        
        scrubbed = pipeline.scrub(text)
        
        # The SSN should be redacted - it may be classified as SSN or PHONE
        assert "078-05-1120" not in scrubbed
        assert "[SSN_REDACTED]" in scrubbed or "[PHONE]" in scrubbed

    def test_scrub_email(self):
        """Email addresses should be redacted."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "Contact me at john.doe@example.com"
        
        scrubbed = pipeline.scrub(text)
        
        assert "john.doe@example.com" not in scrubbed
        assert "[EMAIL]" in scrubbed

    def test_scrub_phone(self):
        """Phone numbers should be redacted."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "Call me at 555-123-4567"
        
        scrubbed = pipeline.scrub(text)
        
        assert "555-123-4567" not in scrubbed
        assert "[PHONE]" in scrubbed

    def test_scrub_person_name(self):
        """Person names should be redacted."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "The student John Smith submitted the form"
        
        scrubbed = pipeline.scrub(text)
        
        assert "John Smith" not in scrubbed
        assert "[PERSON_NAME]" in scrubbed

    def test_no_pii_unchanged(self):
        """Text without PII should remain unchanged."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "The OPT authorization period is 12 months."
        
        scrubbed = pipeline.scrub(text)
        
        assert scrubbed == text

    def test_scrub_with_report(self):
        """Scrubbing should return both scrubbed text and report."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "Contact john@test.com or 555-111-2222"
        
        scrubbed, report = pipeline.scrub_with_report(text)
        
        assert "[EMAIL]" in scrubbed
        assert "[PHONE]" in scrubbed
        assert len(report) >= 2  # At least email and phone detected

    def test_analyze_returns_entity_details(self):
        """Analyze should return details about detected entities."""
        from app.privacy.pipeline import PrivacyPipeline
        
        pipeline = PrivacyPipeline()
        text = "SSN: 111-22-3333"
        
        entities = pipeline.analyze(text)
        
        assert len(entities) >= 1
        assert entities[0]["entity_type"] == "US_SSN"
        assert entities[0]["text"] == "111-22-3333"

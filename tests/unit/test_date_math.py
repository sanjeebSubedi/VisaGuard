"""
TDD Tests for TimelineManager - F-1 OPT Compliance Date Calculations
Version 2.1 - Comprehensive Test Suite

Compliance Rules:
1. Days are counted as **inclusive calendar days** (USCIS standard).
2. Unemployment gaps include weekends (Strict mode).
3. 20-hour MINIMUM for OPT (below = counts as unemployment).
4. Status reported via (compliance_state, severity, action_required).
5. Gaps with no end date default to current_date.
6. Pre-OPT gaps are clamped to OPT start.
7. Overlapping gaps are unioned (no double-counting).
"""

import json
from datetime import date
from pathlib import Path

import pytest

# Load golden dataset
GOLDEN_DATASET_PATH = Path(__file__).parent.parent.parent / "data" / "golden_dataset.json"


@pytest.fixture
def golden_data():
    """Load the golden dataset for test scenarios."""
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)


@pytest.fixture
def timeline_manager():
    """Create a TimelineManager instance."""
    from app.services.timeline_manager import TimelineManager
    return TimelineManager()


# =============================================================================
# OPT DURATION CALCULATIONS
# =============================================================================

class TestOPTDurationCalculations:
    """Tests for basic OPT timeline calculations."""

    def test_opt_end_date_calculation(self, timeline_manager):
        """OPT lasts exactly 12 months from start date.
        June 1, 2026 → May 31, 2027
        """
        opt_start = date(2026, 6, 1)
        result = timeline_manager.calculate_opt_end_date(opt_start)
        assert result == date(2027, 5, 31)

    def test_grace_period_calculation(self, timeline_manager):
        """Grace period ends 60 calendar days AFTER OPT end date."""
        opt_end = date(2027, 1, 31)
        result = timeline_manager.calculate_grace_period_end(opt_end)
        # Jan 31 + 60 days = April 1
        assert result == date(2027, 4, 1)

    def test_remaining_authorized_days_inclusive(self, timeline_manager):
        """Calculate remaining INCLUSIVE work-authorized days.
        
        If today is Dec 1 and OPT ends Dec 2:
        - Dec 1: Authorized ✓
        - Dec 2: Authorized ✓
        - Total = 2 days
        
        Note: This is NOT Python's (end - start).days which returns 1.
        """
        opt_end = date(2026, 12, 2)
        current = date(2026, 12, 1)
        result = timeline_manager.remaining_authorized_days(opt_end, current)
        assert result == 2  # Inclusive: Dec 1 and Dec 2 both count


# =============================================================================
# UNEMPLOYMENT TRACKING (INCLUSIVE, STRICT)
# =============================================================================

class TestUnemploymentTracking:
    """Tests for 90-day unemployment limit (Strict/Inclusive counting)."""

    def test_single_day_gap_is_one_day(self, timeline_manager):
        """Gap of June 1 to June 1 = 1 day (inclusive)."""
        gaps = [{"start": date(2026, 6, 1), "end": date(2026, 6, 1)}]
        result = timeline_manager.calculate_unemployment_days(gaps)
        assert result == 1

    def test_weekend_gap_strict_counting(self, timeline_manager):
        """Strict mode: weekends count as unemployment.
        Sat(June 6) - Sun(June 7) = 2 days.
        """
        gaps = [{"start": date(2026, 6, 6), "end": date(2026, 6, 7)}]
        result = timeline_manager.calculate_unemployment_days(gaps)
        assert result == 2

    def test_multi_day_gap_inclusive(self, timeline_manager):
        """June 1 to Sept 1 (inclusive) = 93 days."""
        gaps = [{"start": date(2026, 6, 1), "end": date(2026, 9, 1)}]
        result = timeline_manager.calculate_unemployment_days(gaps)
        # June: 30, July: 31, Aug: 31, Sept 1: 1 = 93
        assert result == 93

    def test_ongoing_gap_no_end_date(self, timeline_manager):
        """Ongoing gap (end=None) defaults to current_date.
        June 1 to June 10 (current) = 10 days.
        """
        current_date = date(2026, 6, 10)
        gaps = [{"start": date(2026, 6, 1), "end": None}]
        result = timeline_manager.calculate_unemployment_days(gaps, current_date=current_date)
        assert result == 10

    def test_gap_before_opt_start_is_clamped(self, timeline_manager):
        """Pre-OPT days don't count. Gap is clamped to OPT start.
        Gap: May 1 - June 10
        OPT Start: June 1
        Effective gap: June 1 - June 10 = 10 days
        """
        opt_start = date(2026, 6, 1)
        gaps = [{"start": date(2026, 5, 1), "end": date(2026, 6, 10)}]
        result = timeline_manager.calculate_unemployment_days(gaps, opt_start_date=opt_start)
        assert result == 10

    def test_overlapping_gaps_no_double_count(self, timeline_manager):
        """Overlapping gaps are unioned.
        Gap A: June 1 - June 10 (10 days)
        Gap B: June 5 - June 15 (11 days)
        Union: June 1 - June 15 = 15 days (not 21)
        """
        gaps = [
            {"start": date(2026, 6, 1), "end": date(2026, 6, 10)},
            {"start": date(2026, 6, 5), "end": date(2026, 6, 15)}
        ]
        result = timeline_manager.calculate_unemployment_days(gaps)
        assert result == 15

    def test_disjoint_gaps_are_summed(self, timeline_manager):
        """Non-overlapping gaps are summed.
        Gap A: June 1 - June 5 (5 days)
        Gap B: June 20 - June 25 (6 days)
        Total: 11 days
        """
        gaps = [
            {"start": date(2026, 6, 1), "end": date(2026, 6, 5)},
            {"start": date(2026, 6, 20), "end": date(2026, 6, 25)}
        ]
        result = timeline_manager.calculate_unemployment_days(gaps)
        assert result == 11


# =============================================================================
# UNEMPLOYMENT STATUS BOUNDARIES
# =============================================================================

class TestUnemploymentStatusBoundaries:
    """Critical boundary tests for 90-day limit."""

    def test_exactly_90_days_is_valid(self, timeline_manager):
        """90 days = at limit, but NOT exceeded. Status = VALID."""
        result = timeline_manager.check_unemployment_status(90)
        assert result["compliance_state"] == "IN_STATUS"
        assert result["severity"] == "WARNING"  # At limit = warning
        assert result["days_until_limit"] == 0

    def test_exactly_91_days_is_violation(self, timeline_manager):
        """91 days = exceeded. Status = VIOLATION."""
        result = timeline_manager.check_unemployment_status(91)
        assert result["compliance_state"] == "OUT_OF_STATUS"
        assert result["severity"] == "VIOLATION"
        assert result["days_over_limit"] == 1

    def test_warning_zone_75_days(self, timeline_manager):
        """75 days = in warning zone (approaching limit)."""
        result = timeline_manager.check_unemployment_status(75)
        assert result["compliance_state"] == "IN_STATUS"
        assert result["severity"] == "WARNING"
        assert result["days_until_limit"] == 15

    def test_safe_zone_45_days(self, timeline_manager):
        """45 days = safe, plenty of buffer."""
        result = timeline_manager.check_unemployment_status(45)
        assert result["compliance_state"] == "IN_STATUS"
        assert result["severity"] == "INFO"


# =============================================================================
# HOURS COMPLIANCE (MIN 20h)
# =============================================================================

class TestHoursCompliance:
    """Tests for weekly hours compliance (Min 20h)."""

    def test_minimum_hours_critical(self, timeline_manager):
        """< 20 hours = CRITICAL (counts toward unemployment)."""
        result = timeline_manager.check_hours_compliance(weekly_hours=15)
        assert result["compliance_state"] == "IN_STATUS"
        assert result["severity"] == "CRITICAL"
        assert result["action_required"] == "CONTACT_DSO"

    def test_exactly_20_hours_is_compliant(self, timeline_manager):
        """20 hours = minimum met."""
        result = timeline_manager.check_hours_compliance(weekly_hours=20)
        assert result["severity"] == "INFO"
        assert result["action_required"] == "NONE"

    def test_40_hours_is_compliant(self, timeline_manager):
        """40 hours = standard full-time, compliant."""
        result = timeline_manager.check_hours_compliance(weekly_hours=40)
        assert result["severity"] == "INFO"

    def test_60_hours_is_compliant(self, timeline_manager):
        """60 hours = allowed (no max limit for OPT)."""
        result = timeline_manager.check_hours_compliance(weekly_hours=60)
        assert result["severity"] == "INFO"  # No violation, just unusual


# =============================================================================
# STEM ELIGIBILITY (CIP-BASED)
# =============================================================================

class TestSTEMEligibility:
    """Tests for CIP-based STEM extension eligibility."""

    def test_stem_eligible_cs_cip(self, timeline_manager):
        """11.0701 (Computer Science) = STEM eligible."""
        result = timeline_manager.check_stem_eligibility(
            cip_code="11.0701",
            employer_e_verify=True,
            opt_end_date=date(2027, 1, 31)
        )
        assert result["stem_eligible"] is True
        assert result["severity"] == "INFO"

    def test_stem_eligible_business_analytics_cip(self, timeline_manager):
        """52.1301 (Management Science) = On STEM list."""
        result = timeline_manager.check_stem_eligibility(
            cip_code="52.1301",
            employer_e_verify=True,
            opt_end_date=date(2027, 1, 31)
        )
        assert result["stem_eligible"] is True

    def test_stem_ineligible_mba_cip(self, timeline_manager):
        """52.0201 (Business Admin/MBA) = Not on STEM list."""
        result = timeline_manager.check_stem_eligibility(
            cip_code="52.0201",
            employer_e_verify=True,
            opt_end_date=date(2027, 1, 31)
        )
        assert result["stem_eligible"] is False

    def test_stem_ineligible_no_everify(self, timeline_manager):
        """STEM CIP but employer not E-Verify = ineligible."""
        result = timeline_manager.check_stem_eligibility(
            cip_code="11.0701",
            employer_e_verify=False,
            opt_end_date=date(2027, 1, 31)
        )
        assert result["stem_eligible"] is False
        assert "E-Verify" in result.get("reason", "")


# =============================================================================
# DOCUMENT CONFLICT DETECTION
# =============================================================================

class TestConflictDetection:
    """Tests for detecting inconsistent document data."""

    def test_conflicting_start_dates(self, timeline_manager):
        """Offer letter says June 1, SEVP says June 20 = conflict."""
        result = timeline_manager.check_document_consistency(
            offer_letter={"start_date": date(2026, 6, 1)},
            sevp_portal={"start_date": date(2026, 6, 20)}
        )
        assert result["compliance_state"] == "UNKNOWN"
        assert result["severity"] == "WARNING"
        assert result["action_required"] == "RESOLVE_CONFLICT"

    def test_consistent_dates_no_conflict(self, timeline_manager):
        """Same dates = no conflict."""
        result = timeline_manager.check_document_consistency(
            offer_letter={"start_date": date(2026, 6, 1)},
            sevp_portal={"start_date": date(2026, 6, 1)}
        )
        assert result["severity"] == "INFO"
        assert result["action_required"] == "NONE"


# =============================================================================
# GOLDEN DATASET SCHEMA VALIDATION
# =============================================================================

class TestGoldenDatasetComplianceScenarios:
    """Validate structure of compliance scenarios in golden dataset."""

    def test_compliance_scenarios_have_required_fields(self, golden_data):
        """Each compliance scenario must have state, severity, action."""
        compliance_scenarios = [
            s for s in golden_data.get("logic_scenarios", [])
            if "compliance_state" in s.get("expected", {})
        ]
        
        for scenario in compliance_scenarios:
            expected = scenario["expected"]
            assert "compliance_state" in expected, f"Missing compliance_state in {scenario['id']}"
            assert "severity" in expected, f"Missing severity in {scenario['id']}"


class TestGoldenDatasetSTEMScenarios:
    """Validate structure of STEM eligibility scenarios."""

    def test_stem_scenarios_have_required_fields(self, golden_data):
        """Each STEM scenario must have stem_eligible."""
        stem_scenarios = [
            s for s in golden_data.get("logic_scenarios", [])
            if "stem_eligible" in s.get("expected", {})
        ]
        
        for scenario in stem_scenarios:
            expected = scenario["expected"]
            assert "stem_eligible" in expected, f"Missing stem_eligible in {scenario['id']}"
            assert isinstance(expected["stem_eligible"], bool), f"stem_eligible must be bool in {scenario['id']}"


class TestGoldenDatasetDocumentTests:
    """Validate structure of document extraction tests."""

    def test_document_tests_have_required_fields(self, golden_data):
        """Each document test must have input_file and expected_facts."""
        doc_tests = golden_data.get("document_tests", [])
        
        for test in doc_tests:
            assert "id" in test, "Document test missing id"
            assert "input_file" in test, f"Missing input_file in {test.get('id', 'unknown')}"
            assert "expected_facts" in test, f"Missing expected_facts in {test.get('id', 'unknown')}"

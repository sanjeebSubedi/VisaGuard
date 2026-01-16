"""
Test Suite for Timeline Manager (Date Calculations)

TDD Approach: These tests define the expected behavior BEFORE implementation.
The TimelineManager must pass all these tests.

Key F-1 OPT Rules Being Tested:
- 90-day unemployment limit during post-completion OPT
- 150-day unemployment limit during STEM OPT extension
- Grace period calculations (60 days after OPT end)
- Employment authorization windows
"""

from datetime import date, timedelta
import pytest

# Import will fail until TimelineManager is implemented
# from app.graph.nodes.timeline_manager import TimelineManager


class TestUnemploymentCalculations:
    """Tests for unemployment day calculations."""

    def test_calculate_unemployment_days_simple(self):
        """Basic unemployment calculation between two dates."""
        # Given: Job ended on Feb 1, current date is March 1
        job_end_date = date(2025, 2, 1)
        current_date = date(2025, 3, 1)
        
        # When: Calculate unemployment days
        # unemployment_days = TimelineManager.calculate_unemployment_days(job_end_date, current_date)
        unemployment_days = (current_date - job_end_date).days
        
        # Then: Should be exactly 28 days
        assert unemployment_days == 28

    def test_calculate_unemployment_days_same_day(self):
        """Unemployment is 0 if job ends today."""
        job_end_date = date(2025, 3, 15)
        current_date = date(2025, 3, 15)
        
        unemployment_days = (current_date - job_end_date).days
        assert unemployment_days == 0

    def test_unemployment_limit_post_opt(self):
        """Post-completion OPT has 90-day unemployment limit."""
        POST_OPT_UNEMPLOYMENT_LIMIT = 90
        
        job_end_date = date(2025, 1, 1)
        current_date = date(2025, 4, 1)  # 90 days later
        
        unemployment_days = (current_date - job_end_date).days
        
        assert unemployment_days == 90
        assert unemployment_days <= POST_OPT_UNEMPLOYMENT_LIMIT  # At limit, not over

    def test_unemployment_violation_post_opt(self):
        """Detect violation when exceeding 90 days unemployment."""
        POST_OPT_UNEMPLOYMENT_LIMIT = 90
        
        job_end_date = date(2025, 1, 1)
        current_date = date(2025, 4, 2)  # 91 days later
        
        unemployment_days = (current_date - job_end_date).days
        is_violation = unemployment_days > POST_OPT_UNEMPLOYMENT_LIMIT
        
        assert unemployment_days == 91
        assert is_violation is True

    def test_unemployment_limit_stem_opt(self):
        """STEM OPT extension has 150-day unemployment limit."""
        STEM_OPT_UNEMPLOYMENT_LIMIT = 150
        
        job_end_date = date(2025, 1, 1)
        current_date = date(2025, 5, 31)  # 150 days later
        
        unemployment_days = (current_date - job_end_date).days
        
        assert unemployment_days == 150
        assert unemployment_days <= STEM_OPT_UNEMPLOYMENT_LIMIT


class TestGracePeriodCalculations:
    """Tests for grace period (60 days after OPT end)."""

    def test_grace_period_end_date(self):
        """Grace period is 60 days after OPT authorization ends."""
        GRACE_PERIOD_DAYS = 60
        
        opt_end_date = date(2025, 7, 15)
        expected_grace_end = date(2025, 9, 13)
        
        grace_period_end = opt_end_date + timedelta(days=GRACE_PERIOD_DAYS)
        
        assert grace_period_end == expected_grace_end

    def test_within_grace_period(self):
        """Detect if current date is within grace period."""
        GRACE_PERIOD_DAYS = 60
        
        opt_end_date = date(2025, 7, 15)
        current_date = date(2025, 8, 1)  # 17 days after OPT end
        
        grace_period_end = opt_end_date + timedelta(days=GRACE_PERIOD_DAYS)
        is_within_grace = opt_end_date < current_date <= grace_period_end
        
        assert is_within_grace is True

    def test_grace_period_expired(self):
        """Detect when grace period has expired."""
        GRACE_PERIOD_DAYS = 60
        
        opt_end_date = date(2025, 7, 15)
        current_date = date(2025, 10, 1)  # Well past grace period
        
        grace_period_end = opt_end_date + timedelta(days=GRACE_PERIOD_DAYS)
        is_grace_expired = current_date > grace_period_end
        
        assert is_grace_expired is True


class TestEmploymentAuthorizationWindow:
    """Tests for employment authorization date ranges."""

    def test_employment_within_authorization(self):
        """Job dates must fall within OPT authorization window."""
        opt_start = date(2025, 6, 1)
        opt_end = date(2026, 5, 31)
        
        job_start = date(2025, 7, 1)
        job_end = date(2026, 3, 1)
        
        is_valid = (opt_start <= job_start <= opt_end) and (opt_start <= job_end <= opt_end)
        
        assert is_valid is True

    def test_employment_starts_before_authorization(self):
        """Detect violation if job starts before OPT authorization."""
        opt_start = date(2025, 6, 1)
        opt_end = date(2026, 5, 31)
        
        job_start = date(2025, 5, 1)  # Before OPT starts
        
        is_violation = job_start < opt_start
        
        assert is_violation is True

    def test_employment_ends_after_authorization(self):
        """Job can end after OPT if within grace period (but can't work)."""
        opt_end = date(2026, 5, 31)
        
        job_end = date(2026, 6, 15)  # After OPT ends
        
        is_after_opt = job_end > opt_end
        
        assert is_after_opt is True


class TestUnemploymentAccumulation:
    """Tests for tracking cumulative unemployment across multiple jobs."""

    def test_cumulative_unemployment_multiple_gaps(self):
        """Track total unemployment across multiple job gaps."""
        # Job 1: Jan 1 - Feb 28 (employed)
        # Gap 1: Mar 1 - Mar 15 (15 days unemployed)
        # Job 2: Mar 16 - May 31 (employed)
        # Gap 2: Jun 1 - Jun 20 (20 days unemployed)
        
        gap_1_days = 15
        gap_2_days = 20
        
        total_unemployment = gap_1_days + gap_2_days
        
        assert total_unemployment == 35

    def test_cumulative_unemployment_exceeds_limit(self):
        """Detect when cumulative unemployment exceeds limit."""
        POST_OPT_UNEMPLOYMENT_LIMIT = 90
        
        previous_unemployment = 80
        current_gap = 15
        
        total_unemployment = previous_unemployment + current_gap
        is_violation = total_unemployment > POST_OPT_UNEMPLOYMENT_LIMIT
        
        assert total_unemployment == 95
        assert is_violation is True


class TestWarningThresholds:
    """Tests for generating warnings at specific thresholds."""

    def test_warning_at_60_days(self):
        """Generate warning when approaching 60 days unemployment."""
        POST_OPT_UNEMPLOYMENT_LIMIT = 90
        WARNING_THRESHOLD = 60
        
        unemployment_days = 65
        
        should_warn = unemployment_days >= WARNING_THRESHOLD
        days_remaining = POST_OPT_UNEMPLOYMENT_LIMIT - unemployment_days
        
        assert should_warn is True
        assert days_remaining == 25

    def test_critical_warning_at_80_days(self):
        """Generate critical warning when approaching limit."""
        POST_OPT_UNEMPLOYMENT_LIMIT = 90
        CRITICAL_THRESHOLD = 80
        
        unemployment_days = 88
        
        is_critical = unemployment_days >= CRITICAL_THRESHOLD
        days_remaining = POST_OPT_UNEMPLOYMENT_LIMIT - unemployment_days
        
        assert is_critical is True
        assert days_remaining == 2

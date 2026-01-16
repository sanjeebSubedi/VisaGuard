"""
Timeline Manager - Deterministic Date Calculations

This is a LangGraph node that handles ALL date-related calculations with 100%
mathematical precision. LLMs are bad at math - this node ensures deadlines
are calculated correctly.

Key calculations:
- Unemployment day tracking (90 days for post-OPT, 150 for STEM)
- Grace period calculations (60 days after OPT end)
- Employment authorization window validation
- Warning thresholds at 60, 80, and 88 days

This node receives state, performs calculations, and returns updated state.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class OPTType(str, Enum):
    """Types of OPT authorization."""
    POST_COMPLETION = "post_completion"
    STEM_EXTENSION = "stem_extension"


class WarningLevel(str, Enum):
    """Warning severity levels."""
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    VIOLATION = "violation"


# Regulatory constants (these are from 8 CFR 214.2(f))
UNEMPLOYMENT_LIMIT_POST_OPT = 90  # days
UNEMPLOYMENT_LIMIT_STEM_OPT = 150  # days (cumulative with post-OPT)
GRACE_PERIOD_DAYS = 60
WARNING_THRESHOLD_EARLY = 60  # days
WARNING_THRESHOLD_CRITICAL = 80  # days
MIN_HOURS_PER_WEEK_STEM = 20
EMPLOYER_CHANGE_REPORT_DAYS = 10


@dataclass
class TimelineState:
    """
    State object for timeline calculations.
    
    This represents the student's current temporal state in the OPT process.
    """
    opt_type: OPTType
    opt_start_date: date
    opt_end_date: date
    current_date: date
    
    # Employment tracking
    cumulative_unemployment_days: int = 0
    last_employment_end_date: Optional[date] = None
    is_currently_employed: bool = False
    
    # Computed values (filled by TimelineManager)
    days_until_opt_end: int = 0
    is_in_grace_period: bool = False
    grace_period_end_date: Optional[date] = None
    days_remaining_in_grace: int = 0
    unemployment_limit: int = UNEMPLOYMENT_LIMIT_POST_OPT
    unemployment_days_remaining: int = UNEMPLOYMENT_LIMIT_POST_OPT
    warning_level: WarningLevel = WarningLevel.NONE
    warning_message: str = ""


class TimelineManager:
    """
    Deterministic timeline calculator for F-1 OPT compliance.
    
    Usage:
        manager = TimelineManager()
        state = manager.calculate(state)
    
    All date math is done in Python - never ask the LLM to calculate dates.
    """
    
    @staticmethod
    def calculate_unemployment_days(
        last_job_end: date,
        current_date: date,
        previous_unemployment: int = 0
    ) -> int:
        """
        Calculate total unemployment days.
        
        Args:
            last_job_end: Date the last job ended.
            current_date: Today's date.
            previous_unemployment: Days of unemployment already accumulated.
            
        Returns:
            Total cumulative unemployment days.
        """
        if last_job_end is None:
            return previous_unemployment
        
        gap_days = (current_date - last_job_end).days
        return previous_unemployment + max(0, gap_days)
    
    @staticmethod
    def calculate_grace_period(opt_end_date: date) -> tuple[date, bool, int]:
        """
        Calculate grace period details.
        
        Args:
            opt_end_date: Date OPT authorization ends.
            
        Returns:
            Tuple of (grace_period_end_date, is_past_opt_end, days_into_grace).
        """
        grace_end = opt_end_date + timedelta(days=GRACE_PERIOD_DAYS)
        return grace_end, opt_end_date, GRACE_PERIOD_DAYS
    
    @staticmethod
    def get_unemployment_limit(opt_type: OPTType) -> int:
        """Get the unemployment day limit based on OPT type."""
        if opt_type == OPTType.STEM_EXTENSION:
            return UNEMPLOYMENT_LIMIT_STEM_OPT
        return UNEMPLOYMENT_LIMIT_POST_OPT
    
    @staticmethod
    def determine_warning_level(
        unemployment_days: int,
        unemployment_limit: int,
        is_currently_employed: bool
    ) -> tuple[WarningLevel, str]:
        """
        Determine the warning level based on unemployment status.
        
        Returns:
            Tuple of (warning_level, warning_message).
        """
        if is_currently_employed:
            return WarningLevel.NONE, "Currently employed."
        
        days_remaining = unemployment_limit - unemployment_days
        
        if days_remaining < 0:
            return (
                WarningLevel.VIOLATION,
                f"VIOLATION: Exceeded unemployment limit by {abs(days_remaining)} days."
            )
        
        if days_remaining <= 2:
            return (
                WarningLevel.CRITICAL,
                f"CRITICAL: Only {days_remaining} days of unemployment allowance remaining!"
            )
        
        if unemployment_days >= WARNING_THRESHOLD_CRITICAL:
            return (
                WarningLevel.CRITICAL,
                f"CRITICAL: {unemployment_days}/{unemployment_limit} unemployment days used. "
                f"Only {days_remaining} days remaining."
            )
        
        if unemployment_days >= WARNING_THRESHOLD_EARLY:
            return (
                WarningLevel.WARNING,
                f"WARNING: {unemployment_days}/{unemployment_limit} unemployment days used. "
                f"{days_remaining} days remaining."
            )
        
        return (
            WarningLevel.INFO,
            f"OK: {unemployment_days}/{unemployment_limit} unemployment days used. "
            f"{days_remaining} days remaining."
        )
    
    def calculate(self, state: TimelineState) -> TimelineState:
        """
        Perform all timeline calculations and update state.
        
        This is the main entry point - call this from the LangGraph node.
        
        Args:
            state: Current timeline state with raw data.
            
        Returns:
            Updated state with all computed values filled in.
        """
        # 1. Set unemployment limit based on OPT type
        state.unemployment_limit = self.get_unemployment_limit(state.opt_type)
        
        # 2. Calculate days until OPT ends
        state.days_until_opt_end = (state.opt_end_date - state.current_date).days
        
        # 3. Calculate grace period
        state.grace_period_end_date = state.opt_end_date + timedelta(days=GRACE_PERIOD_DAYS)
        state.is_in_grace_period = (
            state.current_date > state.opt_end_date and
            state.current_date <= state.grace_period_end_date
        )
        if state.is_in_grace_period:
            state.days_remaining_in_grace = (
                state.grace_period_end_date - state.current_date
            ).days
        else:
            state.days_remaining_in_grace = 0
        
        # 4. Calculate unemployment days (if not currently employed)
        if not state.is_currently_employed and state.last_employment_end_date:
            current_gap = (state.current_date - state.last_employment_end_date).days
            state.cumulative_unemployment_days += max(0, current_gap)
        
        state.unemployment_days_remaining = (
            state.unemployment_limit - state.cumulative_unemployment_days
        )
        
        # 5. Determine warning level
        state.warning_level, state.warning_message = self.determine_warning_level(
            state.cumulative_unemployment_days,
            state.unemployment_limit,
            state.is_currently_employed
        )
        
        return state
    
    def validate_employment_dates(
        self,
        job_start: date,
        job_end: date,
        opt_start: date,
        opt_end: date
    ) -> tuple[bool, str]:
        """
        Validate that employment dates fall within OPT authorization window.
        
        Returns:
            Tuple of (is_valid, message).
        """
        errors = []
        
        if job_start < opt_start:
            errors.append(
                f"Job starts ({job_start}) before OPT authorization ({opt_start})."
            )
        
        if job_start > opt_end:
            errors.append(
                f"Job starts ({job_start}) after OPT authorization ends ({opt_end})."
            )
        
        # Job can technically end during grace period, but can't work during grace
        # This is just a warning, not a violation
        
        if errors:
            return False, " ".join(errors)
        
        return True, "Employment dates are within authorization window."
    
    def check_reporting_deadline(
        self,
        event_date: date,
        report_date: date,
        deadline_days: int = EMPLOYER_CHANGE_REPORT_DAYS
    ) -> tuple[bool, int]:
        """
        Check if an event was reported within the required deadline.
        
        Args:
            event_date: Date the event occurred (e.g., employer change).
            report_date: Date the event was reported.
            deadline_days: Required reporting window (default: 10 days).
            
        Returns:
            Tuple of (is_on_time, days_late).
        """
        days_to_report = (report_date - event_date).days
        
        if days_to_report <= deadline_days:
            return True, 0
        
        return False, days_to_report - deadline_days


# Convenience function for LangGraph node
def timeline_manager_node(state: dict) -> dict:
    """
    LangGraph node wrapper for TimelineManager.
    
    This function can be used directly as a node in the graph.
    Converts dict state to TimelineState, processes, and returns dict.
    """
    manager = TimelineManager()
    
    # Parse dates from strings if needed
    timeline_state = TimelineState(
        opt_type=OPTType(state.get("opt_type", "post_completion")),
        opt_start_date=_parse_date(state.get("opt_start_date")),
        opt_end_date=_parse_date(state.get("opt_end_date")),
        current_date=_parse_date(state.get("current_date", date.today())),
        cumulative_unemployment_days=state.get("cumulative_unemployment_days", 0),
        last_employment_end_date=_parse_date(state.get("last_employment_end_date")),
        is_currently_employed=state.get("is_currently_employed", False),
    )
    
    # Calculate
    result = manager.calculate(timeline_state)
    
    # Return updated state as dict
    return {
        **state,
        "timeline": {
            "opt_type": result.opt_type.value,
            "days_until_opt_end": result.days_until_opt_end,
            "is_in_grace_period": result.is_in_grace_period,
            "grace_period_end_date": str(result.grace_period_end_date) if result.grace_period_end_date else None,
            "days_remaining_in_grace": result.days_remaining_in_grace,
            "unemployment_days": result.cumulative_unemployment_days,
            "unemployment_limit": result.unemployment_limit,
            "unemployment_days_remaining": result.unemployment_days_remaining,
            "warning_level": result.warning_level.value,
            "warning_message": result.warning_message,
        }
    }


def _parse_date(value) -> Optional[date]:
    """Parse a date from string or return as-is if already a date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return None

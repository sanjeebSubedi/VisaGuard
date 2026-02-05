"""
TimelineManager v2.0 - F-1 OPT Compliance Date Calculator

Pure Python implementation for calculating F-1 visa compliance dates and statuses.
No LLM calls, no external APIs, no PII handling.

Compliance Rules:
- Days are counted INCLUSIVELY (USCIS standard)
- Unemployment gaps are unioned (no double-counting)
- 20-hour minimum for OPT employment
- 90-day unemployment limit (150 for STEM)
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set


# =============================================================================
# STEM CIP CODES (Subset - real list has 400+ codes)
# =============================================================================

STEM_CIP_CODES: Set[str] = {
    # Computer Science
    "11.0101", "11.0701",
    # Engineering
    "14.0101", "14.0901",
    # Mathematics
    "27.0101", "27.0301",
    # Physical Sciences
    "40.0101", "40.0801",
    # Business Analytics / Management Science (STEM-designated)
    "52.1301",
}


# =============================================================================
# TIMELINE MANAGER
# =============================================================================

class TimelineManager:
    """
    Pure Python logic for F-1 OPT compliance calculations.
    
    All date arithmetic uses inclusive counting (USCIS standard).
    Unemployment tracking uses Set-based union for overlap handling.
    """

    # Duration constants
    OPT_DURATION_DAYS: int = 365
    GRACE_PERIOD_DAYS: int = 60
    STEM_EXTENSION_DAYS: int = 730  # 24 months

    # Unemployment limits
    UNEMPLOYMENT_LIMIT_DAYS: int = 90
    STEM_UNEMPLOYMENT_LIMIT_DAYS: int = 150
    WARNING_THRESHOLD_DAYS: int = 15  # Warn when < 15 days remaining

    # Employment requirements
    MIN_WEEKLY_HOURS: int = 20

    # -------------------------------------------------------------------------
    # OPT Duration Calculations
    # -------------------------------------------------------------------------

    def calculate_opt_end_date(self, opt_start: date) -> date:
        """
        Calculate OPT end date (exactly 12 months from start).
        
        Example: June 1, 2026 → May 31, 2027
        
        Uses year replacement for accurate month handling.
        Falls back to day arithmetic for Feb 29 edge case.
        """
        try:
            # Same date next year, minus 1 day
            next_year_same_date = opt_start.replace(year=opt_start.year + 1)
            return next_year_same_date - timedelta(days=1)
        except ValueError:
            # Feb 29 in leap year → use day arithmetic
            return opt_start + timedelta(days=self.OPT_DURATION_DAYS - 1)

    def calculate_grace_period_end(self, opt_end_date: date) -> date:
        """
        Calculate grace period end (60 days after OPT ends).
        
        During grace period, student can remain in US but cannot work.
        """
        return opt_end_date + timedelta(days=self.GRACE_PERIOD_DAYS)

    def remaining_authorized_days(self, end_date: date, current_date: date) -> int:
        """
        Calculate INCLUSIVE remaining work-authorized days.
        
        If today is Dec 1 and end is Dec 2:
        - Dec 1: Authorized ✓
        - Dec 2: Authorized ✓
        - Returns: 2
        
        This differs from Python's (end - start).days which returns 1.
        """
        if current_date > end_date:
            return 0
        return (end_date - current_date).days + 1

    # -------------------------------------------------------------------------
    # Unemployment Tracking (Set-Based Union)
    # -------------------------------------------------------------------------

    def calculate_unemployment_days(
        self,
        gaps: List[Dict[str, Optional[date]]],
        current_date: Optional[date] = None,
        opt_start_date: Optional[date] = None
    ) -> int:
        """
        Calculate total unique unemployment days across all gaps.
        
        Handles:
        - Overlapping gaps (via Set union - no double counting)
        - Open-ended gaps (end=None defaults to current_date)
        - Pre-OPT gaps (clamped to opt_start_date)
        - Inclusive counting (start to end, both included)
        
        Args:
            gaps: List of {"start": date, "end": date|None}
            current_date: Reference date for open-ended gaps
            opt_start_date: Clamp gaps to this date (pre-OPT doesn't count)
            
        Returns:
            Total unique unemployment days
        """
        unemployment_dates: Set[date] = set()
        effective_current = current_date or date.today()

        for gap in gaps:
            start = gap.get("start")
            end = gap.get("end")

            if start is None:
                continue

            # Handle open-ended gap (ongoing unemployment)
            if end is None:
                end = effective_current

            # Clamp to OPT start (pre-OPT days don't count)
            if opt_start_date and start < opt_start_date:
                start = opt_start_date

            # Skip invalid gaps (start after end)
            if start > end:
                continue

            # Add all days in range to set (handles overlaps automatically)
            num_days = (end - start).days + 1  # Inclusive
            for i in range(num_days):
                unemployment_dates.add(start + timedelta(days=i))

        return len(unemployment_dates)

    def check_unemployment_status(
        self, 
        days_used: int, 
        is_stem: bool = False
    ) -> Dict[str, Any]:
        """
        Check unemployment status against limit.
        
        Returns:
            compliance_state: "IN_STATUS" or "OUT_OF_STATUS"
            severity: "INFO", "WARNING", or "VIOLATION"
            days_until_limit: (if under limit)
            days_over_limit: (if over limit)
        """
        limit = self.STEM_UNEMPLOYMENT_LIMIT_DAYS if is_stem else self.UNEMPLOYMENT_LIMIT_DAYS
        remaining = limit - days_used

        # Over limit = VIOLATION
        if days_used > limit:
            return {
                "compliance_state": "OUT_OF_STATUS",
                "severity": "VIOLATION",
                "action_required": "CONTACT_DSO",
                "days_over_limit": days_used - limit,
                "limit": limit,
            }

        # At or near limit = WARNING
        if remaining <= self.WARNING_THRESHOLD_DAYS:
            return {
                "compliance_state": "IN_STATUS",
                "severity": "WARNING",
                "action_required": "NONE",
                "days_until_limit": remaining,
                "limit": limit,
            }

        # Safe zone = INFO
        return {
            "compliance_state": "IN_STATUS",
            "severity": "INFO",
            "action_required": "NONE",
            "days_until_limit": remaining,
            "limit": limit,
        }

    # -------------------------------------------------------------------------
    # Hours Compliance
    # -------------------------------------------------------------------------

    def check_hours_compliance(self, weekly_hours: int) -> Dict[str, Any]:
        """
        Check weekly hours against OPT minimum requirement.
        
        < 20 hours: CRITICAL (counts as unemployment)
        >= 20 hours: Compliant
        
        Note: OPT has NO maximum hour limit. 60+ hours is legal.
        """
        if weekly_hours < self.MIN_WEEKLY_HOURS:
            return {
                "compliance_state": "IN_STATUS",
                "severity": "CRITICAL",
                "action_required": "CONTACT_DSO",
                "message": f"Hours {weekly_hours} below minimum {self.MIN_WEEKLY_HOURS}. May count as unemployment.",
            }

        return {
            "compliance_state": "IN_STATUS",
            "severity": "INFO",
            "action_required": "NONE",
            "message": "Hours compliant.",
        }

    # -------------------------------------------------------------------------
    # STEM Extension Eligibility
    # -------------------------------------------------------------------------

    def check_stem_eligibility(
        self,
        cip_code: str,
        employer_e_verify: bool,
        opt_end_date: date
    ) -> Dict[str, Any]:
        """
        Check STEM OPT extension eligibility.
        
        Requirements:
        1. Degree CIP code on STEM Designated Degree List
        2. Employer enrolled in E-Verify
        
        Returns potential extension end date if eligible.
        """
        # Check CIP code
        if cip_code not in STEM_CIP_CODES:
            return {
                "stem_eligible": False,
                "severity": "INFO",
                "reason": f"CIP {cip_code} not on STEM list",
            }

        # Check E-Verify
        if not employer_e_verify:
            return {
                "stem_eligible": False,
                "severity": "INFO",
                "reason": "Employer must be enrolled in E-Verify",
            }

        # Eligible - calculate extension end date
        try:
            potential_end = opt_end_date.replace(year=opt_end_date.year + 2)
        except ValueError:
            # Feb 29 edge case
            potential_end = opt_end_date + timedelta(days=self.STEM_EXTENSION_DAYS)

        return {
            "stem_eligible": True,
            "severity": "INFO",
            "potential_end_date": potential_end,
        }

    # -------------------------------------------------------------------------
    # Document Consistency Check
    # -------------------------------------------------------------------------

    def check_document_consistency(
        self,
        offer_letter: Optional[Dict[str, Any]] = None,
        sevp_portal: Optional[Dict[str, Any]] = None,
        **other_docs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for conflicts between document data sources.
        
        Compares start_date fields across all provided documents.
        If mismatch found, returns UNKNOWN state with RESOLVE_CONFLICT action.
        """
        all_docs = {}
        if offer_letter:
            all_docs["offer_letter"] = offer_letter
        if sevp_portal:
            all_docs["sevp_portal"] = sevp_portal
        all_docs.update(other_docs)

        # Collect start dates
        start_dates: Dict[str, date] = {}
        for doc_name, fields in all_docs.items():
            if "start_date" in fields and fields["start_date"] is not None:
                start_dates[doc_name] = fields["start_date"]

        # Check for conflicts
        unique_dates = set(start_dates.values())
        if len(unique_dates) > 1:
            return {
                "compliance_state": "UNKNOWN",
                "severity": "WARNING",
                "action_required": "RESOLVE_CONFLICT",
                "details": f"Conflicting start dates: {start_dates}",
            }

        # No conflict
        return {
            "compliance_state": "IN_STATUS",
            "severity": "INFO",
            "action_required": "NONE",
        }

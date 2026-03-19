from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewItemResult:
    review_type: str
    field_name: str
    priority: str = "normal"
    assigned_role: str = "student"
    resolution_status: str = "open"

from __future__ import annotations

from pydantic import BaseModel, Field


class ClockResult(BaseModel):
    status: str
    relevant_dates: dict[str, str] = Field(default_factory=dict)
    missing_prerequisites: list[str] = Field(default_factory=list)
    days_remaining: int | None = None
    limit_days: int | None = None


class DeadlineItem(BaseModel):
    type: str
    due_date: str
    message: str


class RiskFlag(BaseModel):
    type: str
    severity: str
    message: str
    related_clock: str | None = None


class ActionItem(BaseModel):
    type: str
    priority: str
    message: str
    due_date: str | None = None
    related_clock: str | None = None


class TimelineInputs(BaseModel):
    evaluation_date: str
    facts_used: dict[str, list[str]] = Field(default_factory=dict)
    missing_prerequisites: dict[str, list[str]] = Field(default_factory=dict)


class TimelineStatus(BaseModel):
    current_phase: str
    clocks: dict[str, ClockResult] = Field(default_factory=dict)
    deadlines: list[DeadlineItem] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)

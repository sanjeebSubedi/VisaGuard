from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    user_id: str
    evaluation_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class WorkflowResultResponse(BaseModel):
    user_id: str
    evaluation_date: str
    timeline_status: dict
    policy_analysis: dict
    policy_verdict: dict
    final_compliance_record: dict

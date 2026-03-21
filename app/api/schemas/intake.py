from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    document_type: str
    file_fingerprint: str | None
    parse_status: str
    redaction_status: str
    extraction_status: str


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    version: int
    snapshot_payload: dict
    field_eligibility_map: dict
    provenance_map: dict


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    review_type: str
    field_name: str
    priority: str
    assigned_role: str
    resolution_status: str


class ManualEADEntryRequest(BaseModel):
    user_id: str
    alien_registration_number: str
    category: str
    card_start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    card_end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    card_number: str | None = None

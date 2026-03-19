from pydantic import BaseModel, ConfigDict


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

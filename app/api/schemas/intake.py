from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    document_type: str
    encrypted_original_uri: str | None
    file_fingerprint: str | None
    parse_status: str
    redaction_status: str
    extraction_status: str

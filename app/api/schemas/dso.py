from pydantic import BaseModel

from app.services.dso_agent.types import ChatTurn, DSOCitation


class DSOChatRequest(BaseModel):
    user_id: str
    message: str
    chat_history: list[ChatTurn]


class DSOChatResponse(BaseModel):
    answer: str
    citations: list[DSOCitation]
    confidence: str
    needs_human_escalation: bool
    answer_mode: str

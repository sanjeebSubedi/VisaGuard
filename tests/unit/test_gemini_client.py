import pytest
from pydantic import BaseModel

from app.services.reasoning_llm.gemini_client import (
    GeminiReasoningClient,
    GeminiResponseError,
    GeminiUnavailableError,
)


def test_gemini_client_raises_for_missing_api_key():
    with pytest.raises(GeminiUnavailableError, match="Missing GEMINI_API_KEY"):
        GeminiReasoningClient(api_key=None)


def test_gemini_client_returns_structured_payload(monkeypatch):
    class VerdictPayload(BaseModel):
        verdict: str

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            assert model == "gemini-test"
            assert contents == "hello"
            assert config.response_mime_type == "application/json"
            assert config.response_schema is VerdictPayload

            class Response:
                parsed = {"verdict": "directly_related"}

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setattr("app.services.reasoning_llm.gemini_client.genai.Client", FakeClient)

    client = GeminiReasoningClient(api_key="test-key")
    payload = client.generate_structured(model="gemini-test", prompt="hello", schema=VerdictPayload)

    assert payload["verdict"] == "directly_related"


def test_gemini_client_raises_for_malformed_response(monkeypatch):
    class VerdictPayload(BaseModel):
        verdict: str

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            class Response:
                parsed = None

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("app.services.reasoning_llm.gemini_client.genai.Client", FakeClient)

    client = GeminiReasoningClient(api_key="test-key")

    with pytest.raises(GeminiResponseError):
        client.generate_structured(model="gemini-test", prompt="hello", schema=VerdictPayload)

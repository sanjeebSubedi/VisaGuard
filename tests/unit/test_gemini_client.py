import pytest

from app.services.reasoning_llm.gemini_client import (
    GeminiReasoningClient,
    GeminiResponseError,
    GeminiUnavailableError,
)


def test_gemini_client_raises_for_missing_api_key():
    with pytest.raises(GeminiUnavailableError, match="Missing GEMINI_API_KEY"):
        GeminiReasoningClient(api_key=None)


def test_gemini_client_returns_structured_payload(monkeypatch):
    class FakeModels:
        def generate_content(self, *, model, contents):
            assert model == "gemini-test"
            assert contents == "hello"

            class Response:
                text = '{"verdict": "directly_related"}'

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setattr("app.services.reasoning_llm.gemini_client.genai.Client", FakeClient)

    client = GeminiReasoningClient(api_key="test-key")
    payload = client.generate_structured(model="gemini-test", prompt="hello")

    assert payload["verdict"] == "directly_related"


def test_gemini_client_raises_for_malformed_response(monkeypatch):
    class FakeModels:
        def generate_content(self, *, model, contents):
            class Response:
                text = "not-json"

            return Response()

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("app.services.reasoning_llm.gemini_client.genai.Client", FakeClient)

    client = GeminiReasoningClient(api_key="test-key")

    with pytest.raises(GeminiResponseError):
        client.generate_structured(model="gemini-test", prompt="hello")

import pytest

from app.services.llm.ollama_client import OllamaClientAdapter, OllamaUnavailableError


def test_ollama_client_returns_response_text(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.ollama_client.Client",
        lambda host=None, timeout=None: type(
            "FakeClient",
            (),
            {
                "generate": lambda self, model, prompt, options=None: {
                    "response": '{"program_start_date": "2026-08-20"}'
                }
            },
        )(),
    )

    adapter = OllamaClientAdapter(host="http://127.0.0.1:11434", timeout_seconds=30)

    assert adapter.generate(model="qwen3:4b-instruct", prompt="extract") == '{"program_start_date": "2026-08-20"}'


def test_ollama_client_raises_unavailable_error(monkeypatch):
    def fake_client(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.services.llm.ollama_client.Client", fake_client)

    with pytest.raises(OllamaUnavailableError):
        OllamaClientAdapter(host="http://127.0.0.1:11434", timeout_seconds=30)

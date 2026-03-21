from app.core.config import Settings


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'visaguard.db'}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")
    assert settings.storage_root.endswith("storage")


def test_settings_default_ollama_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    settings = Settings()

    assert settings.ollama_model == "qwen3:4b-instruct"


def test_settings_default_ollama_timeout(monkeypatch):
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)

    settings = Settings()

    assert settings.ollama_timeout_seconds == 180



def test_settings_default_policy_paths(monkeypatch):
    monkeypatch.delenv("POLICY_DATA_ROOT", raising=False)
    monkeypatch.delenv("POLICY_INDEX_PATH", raising=False)

    settings = Settings()

    assert settings.policy_data_root == "./data/policy"
    assert settings.policy_index_path == "./data/policy/index/policy_index.json"

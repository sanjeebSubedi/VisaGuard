from app.core.config import Settings


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'visaguard.db'}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")
    assert settings.storage_root.endswith("storage")

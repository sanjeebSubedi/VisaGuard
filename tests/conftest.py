from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.db.models  # noqa: F401
from app.db.session import get_db_session
from app.main import app
from app.services.parsing.docling_parser import ParsedDocument


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def isolated_storage_root(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))


@pytest.fixture(autouse=True)
def stub_pipeline_docling_parse(monkeypatch):
    def fake_parse_with_docling(*, file_bytes: bytes, filename: str, content_type: str) -> ParsedDocument:
        lowered = filename.lower()
        if content_type.startswith("image/"):
            text = "Card Expires: 2027-08-19\nCategory: C03B"
        elif lowered.endswith(".pdf") and "i20" in lowered:
            text = "Program Start Date: 2026-08-20\nCIP Code: 11.0101\nSchool Name: Example University"
        elif lowered.endswith(".pdf") and "offer" in lowered:
            text = (
                "Employer: OpenAI\n"
                "Title: Research Intern\n"
                "Start Date: 2026-09-01\n"
                "Student Name: Ada Lovelace\n"
                "Email: ada@example.com\n"
                "Phone: 555-111-2222\n"
                "SEVIS ID: N0012345678\n"
            )
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
        return ParsedDocument(
            text=text,
            metadata={"pages": 1, "filename": filename, "content_type": content_type},
            raw_payload={"text": text},
        )
    monkeypatch.setattr("app.services.pipeline.parse_with_docling", fake_parse_with_docling)


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

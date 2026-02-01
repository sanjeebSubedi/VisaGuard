"""
Database connection and session management.
"""

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Database location
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATABASE_PATH = DATA_DIR / "visaguard.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine (echo=True for debug SQL logging)
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create all tables if they don't exist."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Import models to register them
    from app.db.models import EADDocument, I20Document, OfferLetterDocument  # noqa

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)


# =============================================================================
# CRUD OPERATIONS
# =============================================================================


def save_i20(session: Session, file_path: str, file_hash: str, fields: dict) -> int:
    """Save an I-20 document to the database."""
    from app.db.models import I20Document

    doc = I20Document(file_path=file_path, file_hash=file_hash, **fields)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc.id


def save_offer_letter(session: Session, file_path: str, file_hash: str, fields: dict) -> int:
    """Save an Offer Letter document to the database."""
    from app.db.models import OfferLetterDocument

    doc = OfferLetterDocument(file_path=file_path, file_hash=file_hash, **fields)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc.id


def save_ead(session: Session, file_path: str, file_hash: str, fields: dict) -> int:
    """Save an EAD document to the database."""
    from app.db.models import EADDocument

    doc = EADDocument(file_path=file_path, file_hash=file_hash, **fields)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc.id


# =============================================================================
# HASHING & CACHE LOOKUP
# =============================================================================


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    import hashlib

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_cached_i20(session: Session, file_hash: str):
    """Check if I-20 with this hash exists. Returns document or None."""
    from sqlmodel import select

    from app.db.models import I20Document

    stmt = select(I20Document).where(I20Document.file_hash == file_hash)
    return session.exec(stmt).first()


def get_cached_offer_letter(session: Session, file_hash: str):
    """Check if Offer Letter with this hash exists. Returns document or None."""
    from sqlmodel import select

    from app.db.models import OfferLetterDocument

    stmt = select(OfferLetterDocument).where(
        OfferLetterDocument.file_hash == file_hash
    )
    return session.exec(stmt).first()


def get_cached_ead(session: Session, file_hash: str):
    """Check if EAD with this hash exists. Returns document or None."""
    from sqlmodel import select

    from app.db.models import EADDocument

    stmt = select(EADDocument).where(EADDocument.file_hash == file_hash)
    return session.exec(stmt).first()


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print(f"Database created at: {DATABASE_PATH}")

    # Verify tables
    from sqlmodel import text

    with get_session() as session:
        result = session.exec(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result]
        print(f"Tables: {tables}")

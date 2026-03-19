from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings


settings = Settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

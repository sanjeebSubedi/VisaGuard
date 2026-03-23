from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.intake import router as intake_router
from app.api.routes.workflows import router as workflows_router
from app.db.base import Base
import app.db.models  # noqa: F401
from app.db.session import build_engine


def initialize_database() -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="VisaGuard Intake Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(intake_router)
app.include_router(workflows_router)

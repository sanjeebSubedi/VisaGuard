from fastapi import FastAPI

from app.api.routes.intake import router as intake_router

app = FastAPI(title="VisaGuard Intake Service")
app.include_router(intake_router)

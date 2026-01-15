from fastapi import FastAPI

app = FastAPI(
    title="VisaGuard API",
    description="Privacy-preserving, multi-agent orchestration for F-1 compliance",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

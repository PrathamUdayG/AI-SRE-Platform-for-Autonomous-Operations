import uvicorn
from fastapi import FastAPI
from src.presentation.api.v1.health import router as health_router

app = FastAPI(
    title="AI SRE Platform",
    description="Autonomous incident response and infrastructure management agent.",
    version="0.1.0"
)

app.include_router(health_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

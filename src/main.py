from fastapi import FastAPI
from src.presentation.api.v1 import router as v1_router
from src.presentation.api.v1.health import router as health_router

app = FastAPI(
    title="AI_SRE Platform",
    description="Autonomous SRE with AI",
    version="0.1.0",
)

# Mount routes
app.include_router(health_router)   # /health and /health/readiness
app.include_router(v1_router)        # /api/v1/...

@app.get("/")
async def root():
    return {"message": "Welcome to AI_SRE Platform", "docs": "/docs"}
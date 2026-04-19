import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import contracts, health, tasks
from backend.config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="LegalLens",
    version="0.1.0",
    description="AI-Powered Contract Risk Analyzer",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["contracts"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

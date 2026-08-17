"""
Peblo TV Mini — FastAPI Application

Main application entry point. Configures:
- CORS
- Route registration
- Health check
- Static file serving for stored artwork
- Database seeding on startup
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine, async_session_factory
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.catalog import router as catalog_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — run seed on startup if needed."""
    from app.db.seed import run_seed
    async with async_session_factory() as db:
        await run_seed(db)
    yield
    await engine.dispose()


app = FastAPI(
    title="Peblo TV Mini",
    description="Content management and catalogue publishing API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(catalog_router)

# Serve stored files (artwork, catalogue)
storage_path = settings.storage_path
os.makedirs(storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")


@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity status."""
    db_status = "healthy"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    storage_status = "healthy" if os.path.isdir(storage_path) else "unhealthy: storage path not found"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "storage": storage_status,
        "version": "1.0.0",
    }

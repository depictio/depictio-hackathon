"""FastAPI WebSocket service for real-time updates."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_service.config import settings
from fastapi_service.services.csv_monitor import csv_watcher
from fastapi_service.websocket.routes import router as ws_router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    logger.info("Starting FastAPI WebSocket Service")

    loop = asyncio.get_event_loop()
    csv_path = Path(settings.DATA_DIR) / "phenobase.csv"
    csv_watcher.start(str(csv_path), loop)

    yield

    logger.info("Shutting down...")
    csv_watcher.stop()


app = FastAPI(
    title="UMAP Explorer WebSocket Service", version="1.0.0", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8050", "http://127.0.0.1:8050"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint."""
    from fastapi_service.websocket.manager import manager

    return {"status": "healthy", "connections": len(manager.active_connections)}


if __name__ == "__main__":
    uvicorn.run(
        "fastapi_service.main:app",
        host="0.0.0.0",
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG,
    )

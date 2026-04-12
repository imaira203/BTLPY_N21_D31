from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, apply_mysql_schema_patches, engine
from .routers import admin, auth, candidate, hr, users
from .storage_paths import upload_dir_for_kind

log = logging.getLogger("jobhub.api")

API_PREFIX = "/api"


def _log_registered_paths(application: FastAPI) -> None:
    paths = sorted({getattr(r, "path", "") for r in application.routes if hasattr(r, "path")})
    sample = [p for p in paths if "health" in p or p.endswith("/login")][:8]
    log.info(
        "JobHub: %d HTTP paths — phải có %s (client 404 = cổng đang là app khác hoặc chưa restart uvicorn).",
        len(paths),
        f"{API_PREFIX}/health",
    )
    log.info("Ví dụ path: %s", sample)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_mysql_schema_patches()
    for kind in ("cvs", "avatars", "hr_assets"):
        upload_dir_for_kind(settings, kind)
    _log_registered_paths(_app)
    yield


app = FastAPI(title="JobHub API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_api_router() -> APIRouter:
    """Một router gom /health + tất cả router nghiệp vụ, mount một lần dưới `/api`."""
    api = APIRouter()

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    for r in (auth.router, users.router, candidate.router, hr.router, admin.router):
        api.include_router(r)
    return api


app.include_router(_build_api_router(), prefix=API_PREFIX)


@app.get("/")
def root() -> dict:
    return {
        "service": "jobhub",
        "api_prefix": API_PREFIX,
        "docs": "/docs",
        "health": f"{API_PREFIX}/health",
    }

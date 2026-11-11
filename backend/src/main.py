"""TSALIGN API entrypoint.

Middleware order (outermost first):
    CORS -> RequestId -> Auth -> RateLimit -> Audit -> routes -> error handlers
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import init_db
from src.config.settings import settings
from src.middlewares.audit_logger import AuditMiddleware
from src.middlewares.auth import AuthMiddleware
from src.middlewares.error_handler import RequestIdMiddleware, install_error_handlers
from src.middlewares.quota import RateLimitMiddleware
from src.routes import auth, gap, health, job, report, run, signal, source
from src.utils.logger import log_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.SEED_DEMO:
        try:
            from scripts.seed_demo import run_seed

            summary = run_seed()
            log_event("SEED_DEMO_FINISHED", summary=summary)
        except Exception as exc:  # seed must never block startup
            log_event("SEED_DEMO_FAILED", error=f"{type(exc).__name__}: {exc}")
    yield


app = FastAPI(
    title="TSALIGN API",
    description="工业时序遥测对齐与缺口修复工作台 — 瀚川重工设备可靠性组",
    version="1.0.0",
    lifespan=lifespan,
)

install_error_handlers(app)

# added first => innermost
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-CSV-Rows", "Content-Disposition"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(source.router)
app.include_router(signal.router)
app.include_router(job.router)
app.include_router(run.router)
app.include_router(gap.router)
app.include_router(report.router)


@app.get("/")
def index() -> dict:
    return {
        "service": "tsalign-backend",
        "customer": "瀚川重工 · 设备可靠性组",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/auth/login",
            "/data-sources",
            "/signals",
            "/alignment-jobs",
            "/alignment-runs/{id}",
            "/alignment-runs/{id}/export.csv",
            "/gap-events",
            "/reports/summary",
        ],
    }

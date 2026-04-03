import logging
import time
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers.alerts import router as alerts_router
from app.routers.auth import router as auth_router
from app.routers.metrics import router as metrics_router
from app.routers.slo import router as slo_router
from app.services.aggregation import compute_rollups
from app.services.simulator import publish_synthetic_metrics
from app.services.slo import evaluate_slos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def initialize_database(max_attempts: int = 20, delay_seconds: int = 2) -> None:
    # Retry DB initialization so containers can start before Postgres is fully ready.
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized on attempt %s", attempt)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Database init attempt %s failed: %s", attempt, exc)
            time.sleep(delay_seconds)

    if last_error:
        raise last_error


def rollup_job() -> None:
    db = SessionLocal()
    try:
        compute_rollups(db)
    finally:
        db.close()


def slo_job() -> None:
    db = SessionLocal()
    try:
        evaluate_slos(db)
    finally:
        db.close()


def simulator_job() -> None:
    db = SessionLocal()
    try:
        publish_synthetic_metrics(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(application: FastAPI):
    initialize_database()
    scheduler.add_job(rollup_job, "interval", seconds=30, id="rollup_job", replace_existing=True)
    scheduler.add_job(slo_job, "interval", seconds=60, id="slo_job", replace_existing=True)
    if settings.enable_internal_simulator:
        interval_seconds = max(1, settings.simulator_interval_seconds)
        scheduler.add_job(
            simulator_job,
            "interval",
            seconds=interval_seconds,
            id="simulator_job",
            replace_existing=True,
        )
        logger.info("Internal simulator enabled; interval=%ss", interval_seconds)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)
app.include_router(slo_router)
app.include_router(alerts_router)
app.include_router(auth_router)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}

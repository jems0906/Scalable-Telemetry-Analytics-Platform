import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Metric
from app.schemas import MetricIn
from app.security import require_roles, verify_access_token
from app.services.aggregation import WINDOWS, compute_rollups, fetch_rollups

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("")
def ingest_metric(payload: MetricIn, db: Session = Depends(get_db)):
    is_error = payload.status_code >= 500
    metric = Metric(
        service_name=payload.service_name,
        timestamp=payload.timestamp or datetime.now(timezone.utc).replace(tzinfo=None),
        cpu_usage=payload.cpu_usage,
        latency_ms=payload.latency_ms,
        status_code=payload.status_code,
        error=is_error,
    )

    db.add(metric)
    db.commit()
    db.refresh(metric)

    return {"status": "accepted", "id": metric.id}


@router.get("/services")
def list_services(db: Session = Depends(get_db), _: str = Depends(require_roles("viewer", "operator"))):
    services = [row[0] for row in db.query(distinct(Metric.service_name)).all() if row[0] is not None]
    return {"services": sorted(services)}


@router.get("/rollups")
def get_rollups(
    window: str = "1m",
    service_name: str | None = None,
    _: str = Depends(require_roles("viewer", "operator")),
):
    if window not in WINDOWS:
        return {"error": f"window must be one of {', '.join(WINDOWS.keys())}"}
    return {"rollups": fetch_rollups(window, service_name)}


@router.post("/rollups/recompute")
def recompute_rollups(db: Session = Depends(get_db), _: str = Depends(require_roles("operator"))):
    rollups = compute_rollups(db)
    return {"status": "ok", "computed": len(rollups)}


@router.websocket("/ws/metrics")
async def stream_metrics(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        payload = verify_access_token(token)
        role = str(payload.get("role", ""))
        if role not in {"viewer", "operator"}:
            await websocket.close(code=1008)
            return
    except Exception:  # noqa: BLE001
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"rollups": fetch_rollups("1m")})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return

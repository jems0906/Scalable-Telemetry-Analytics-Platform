from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.models import Metric
from app.redis_client import redis_client

WINDOWS: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "1h": timedelta(hours=1),
}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    rank = int(round((percentile / 100) * (len(values) - 1)))
    rank = max(0, min(rank, len(values) - 1))
    return float(values[rank])


def _aggregate(metrics: list[Metric], window: str, service_name: str) -> dict:
    if not metrics:
        return {
            "service_name": service_name,
            "window": window,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "samples": 0,
            "error_count": 0,
            "error_rate": 0.0,
            "avg_cpu": 0.0,
            "avg_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

    sample_count = len(metrics)
    error_count = sum(1 for m in metrics if m.error)
    latencies = [m.latency_ms for m in metrics]

    return {
        "service_name": service_name,
        "window": window,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "samples": sample_count,
        "error_count": error_count,
        "error_rate": error_count / sample_count,
        "avg_cpu": sum(m.cpu_usage for m in metrics) / sample_count,
        "avg_latency_ms": sum(latencies) / sample_count,
        "p99_latency_ms": _percentile(latencies, 99),
    }


def compute_rollups(db: Session) -> list[dict]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    services = [
        row[0]
        for row in db.query(distinct(Metric.service_name)).all()
        if row[0] is not None
    ]

    rollups: list[dict] = []

    for window, delta in WINDOWS.items():
        start = now - delta
        window_metrics = db.query(Metric).filter(Metric.timestamp >= start).all()
        all_rollup = _aggregate(window_metrics, window, "all")
        redis_client.setex(f"rollup:{window}:all", int(delta.total_seconds()) * 3, json.dumps(all_rollup))
        rollups.append(all_rollup)

        for service in services:
            metrics = (
                db.query(Metric)
                .filter(Metric.timestamp >= start, Metric.service_name == service)
                .all()
            )
            rollup = _aggregate(metrics, window, service)
            redis_client.setex(f"rollup:{window}:{service}", int(delta.total_seconds()) * 3, json.dumps(rollup))
            rollups.append(rollup)

    return rollups


def fetch_rollups(window: str, service_name: str | None = None) -> list[dict]:
    if service_name:
        key = f"rollup:{window}:{service_name}"
        value = redis_client.get(key)
        return [json.loads(value)] if value else []

    results: list[dict] = []
    for key in redis_client.scan_iter(match=f"rollup:{window}:*"):
        value = redis_client.get(key)
        if value:
            results.append(json.loads(value))
    return sorted(results, key=lambda item: item["service_name"])

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Metric
from app.redis_client import redis_client
from app.services.alerts import emit_alert


def classify_slo_severity(p99_latency_ms: float, error_rate: float) -> str:
    latency_ratio = (
        p99_latency_ms / settings.slo_p99_latency_ms
        if settings.slo_p99_latency_ms > 0
        else 0.0
    )
    error_ratio = (
        error_rate / settings.slo_error_rate
        if settings.slo_error_rate > 0
        else 0.0
    )
    ratio = max(latency_ratio, error_ratio)

    if ratio >= settings.alert_critical_multiplier:
        return "critical"
    if ratio >= settings.alert_major_multiplier:
        return "major"
    return "warning"


def evaluate_slos(db: Session) -> list[dict]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(minutes=5)
    services = [
        row[0]
        for row in db.query(distinct(Metric.service_name)).all()
        if row[0] is not None
    ]

    statuses: list[dict] = []

    for service in services:
        previous_raw = redis_client.get(f"slo:{service}")
        previous_status = json.loads(previous_raw) if previous_raw else None

        records = (
            db.query(Metric)
            .filter(Metric.timestamp >= start, Metric.service_name == service)
            .all()
        )

        if not records:
            continue

        latencies = sorted(item.latency_ms for item in records)
        p99_index = max(0, min(len(latencies) - 1, int(round(0.99 * (len(latencies) - 1)))))
        p99_latency = float(latencies[p99_index])

        error_count = sum(1 for item in records if item.error)
        error_rate = error_count / len(records)

        latency_breached = p99_latency > settings.slo_p99_latency_ms
        error_rate_breached = error_rate > settings.slo_error_rate

        status = {
            "service_name": service,
            "p99_latency_ms": p99_latency,
            "error_rate": error_rate,
            "latency_slo_target_ms": settings.slo_p99_latency_ms,
            "error_rate_slo_target": settings.slo_error_rate,
            "latency_breached": latency_breached,
            "error_rate_breached": error_rate_breached,
            "healthy": not (latency_breached or error_rate_breached),
        }

        redis_client.setex(f"slo:{service}", 1800, json.dumps(status))
        statuses.append(status)

        if latency_breached or error_rate_breached:
            severity = classify_slo_severity(p99_latency, error_rate)
            emit_alert(
                "SLO_BREACH",
                status,
                severity=severity,
                dedup_key=f"alert:dedup:SLO_BREACH:{service}:{severity}",
            )
        elif previous_status and not previous_status.get("healthy", True):
            recovery_payload = {
                "service_name": service,
                "previous": {
                    "p99_latency_ms": previous_status.get("p99_latency_ms"),
                    "error_rate": previous_status.get("error_rate"),
                },
                "current": {
                    "p99_latency_ms": p99_latency,
                    "error_rate": error_rate,
                },
                "message": "Service has recovered and is now healthy.",
            }
            emit_alert(
                "SLO_RECOVERY",
                recovery_payload,
                severity="warning",
                dedup_key=f"alert:dedup:SLO_RECOVERY:{service}",
            )

    return statuses


def fetch_slos(service_name: str | None = None) -> list[dict]:
    if service_name:
        value = redis_client.get(f"slo:{service_name}")
        return [json.loads(value)] if value else []

    results: list[dict] = []
    for key in redis_client.scan_iter(match="slo:*"):
        value = redis_client.get(key)
        if value:
            results.append(json.loads(value))

    return sorted(results, key=lambda item: item["service_name"])

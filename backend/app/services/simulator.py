from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Metric

SERVICES = ["checkout-service", "billing-service", "search-service", "auth-service"]


def _generate_metric(service_name: str) -> Metric:
    latency = random.gauss(180, 120)
    if random.random() < 0.03:
        latency *= random.uniform(2, 5)

    status_code = 200
    if random.random() < 0.02:
        status_code = random.choice([500, 502, 503, 504])

    return Metric(
        service_name=service_name,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        cpu_usage=max(0, min(100, random.gauss(45, 20))),
        latency_ms=max(0, latency),
        status_code=status_code,
        error=status_code >= 500,
    )


def publish_synthetic_metrics(db: Session) -> int:
    metrics = [_generate_metric(service_name) for service_name in SERVICES]
    db.add_all(metrics)
    db.commit()
    return len(metrics)

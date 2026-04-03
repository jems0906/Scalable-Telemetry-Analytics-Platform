import asyncio
import os
import random
from datetime import datetime, timezone

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SERVICES = ["checkout-service", "billing-service", "search-service", "auth-service"]


def generate_metric(service_name: str) -> dict:
    latency = random.gauss(180, 120)
    if random.random() < 0.03:
        latency *= random.uniform(2, 5)

    status_code = 200
    if random.random() < 0.02:
        status_code = random.choice([500, 502, 503, 504])

    return {
        "service_name": service_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_usage": max(0, min(100, random.gauss(45, 20))),
        "latency_ms": max(0, latency),
        "status_code": status_code,
    }


async def publish_metrics() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            tasks = []
            for service in SERVICES:
                payload = generate_metric(service)
                tasks.append(client.post(f"{API_BASE_URL}/metrics", json=payload))
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(publish_metrics())

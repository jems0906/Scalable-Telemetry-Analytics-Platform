from datetime import datetime

from pydantic import BaseModel, Field


class MetricIn(BaseModel):
    service_name: str = Field(min_length=1, max_length=100)
    timestamp: datetime | None = None
    cpu_usage: float = Field(ge=0, le=100)
    latency_ms: float = Field(ge=0)
    status_code: int = Field(ge=100, le=599)

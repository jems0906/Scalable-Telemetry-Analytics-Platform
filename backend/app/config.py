from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TrailMetrics API"
    database_url: str = "postgresql+pg8000://trailmetrics:trailmetrics@localhost:5432/trailmetrics"
    redis_url: str = "redis://localhost:6379/0"
    api_port: int = 8000
    allowed_origins: str = "http://localhost:5173"
    slo_p99_latency_ms: float = 500.0
    slo_error_rate: float = 0.01
    alert_major_multiplier: float = 1.5
    alert_critical_multiplier: float = 2.0
    alert_dedup_cooldown_seconds: int = 300

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60
    auth_admin_username: str = "admin"
    auth_admin_password: str = "admin123"
    auth_operator_username: str = "operator"
    auth_operator_password: str = "operator123"
    auth_viewer_username: str = "viewer"
    auth_viewer_password: str = "viewer123"

    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_from_email: str = "alerts@trailmetrics.local"
    alert_to_email: str = "ops@trailmetrics.local"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        # Render provides postgres:// or postgresql:// URLs by default.
        # SQLAlchemy needs the pg8000 dialect prefix to use the installed driver.
        if value.startswith("postgres://"):
            return "postgresql+pg8000://" + value[len("postgres://") :]

        if value.startswith("postgresql://") and not value.startswith("postgresql+pg8000://"):
            return "postgresql+pg8000://" + value[len("postgresql://") :]

        return value


settings = Settings()

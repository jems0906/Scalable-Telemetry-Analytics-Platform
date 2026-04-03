import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

import httpx

from app.config import settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)
ALERT_HISTORY_KEY = "alerts:history"
ALERT_HISTORY_LIMIT = 500


SEVERITY_COLORS = {
    "warning": "#f59e0b",
    "major": "#f97316",
    "critical": "#ef4444",
}


def _dedup_key(alert_type: str, payload: dict, severity: str) -> str:
    service_name = payload.get("service_name", "global")
    return f"alert:dedup:{alert_type}:{service_name}:{severity}"


def _should_emit_alert(key: str, cooldown_seconds: int) -> bool:
    if redis_client.exists(key):
        return False

    redis_client.setex(key, cooldown_seconds, datetime.now(timezone.utc).isoformat())
    return True


def _store_alert_event(alert_type: str, severity: str, payload: dict, dedup_key: str) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": alert_type,
        "severity": severity,
        "service_name": payload.get("service_name", "global"),
        "payload": payload,
        "dedup_key": dedup_key,
    }

    redis_client.lpush(ALERT_HISTORY_KEY, json.dumps(event))
    redis_client.ltrim(ALERT_HISTORY_KEY, 0, ALERT_HISTORY_LIMIT - 1)


def fetch_alert_history(limit: int = 100) -> list[dict]:
    bounded_limit = max(1, min(limit, ALERT_HISTORY_LIMIT))
    records = redis_client.lrange(ALERT_HISTORY_KEY, 0, bounded_limit - 1)
    return [json.loads(item) for item in records]


def send_slack_alert(slack_payload: dict) -> None:
    if not settings.slack_webhook_url:
        return

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(settings.slack_webhook_url, json=slack_payload)
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Slack alert failed: %s", exc)


def send_email_alert(subject: str, message: str) -> None:
    if not settings.smtp_host:
        return

    mime_message = MIMEText(message)
    mime_message["Subject"] = subject
    mime_message["From"] = settings.alert_from_email
    mime_message["To"] = settings.alert_to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_username:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.sendmail(settings.alert_from_email, [settings.alert_to_email], mime_message.as_string())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email alert failed: %s", exc)


def emit_alert(
    alert_type: str,
    payload: dict,
    severity: str = "warning",
    dedup_key: str | None = None,
) -> None:
    key = dedup_key or _dedup_key(alert_type, payload, severity)
    cooldown = max(1, settings.alert_dedup_cooldown_seconds)

    if not _should_emit_alert(key, cooldown):
        logger.info("Alert suppressed by cooldown for key=%s", key)
        return

    severity_upper = severity.upper()
    message = f"[TrailMetrics][{severity_upper}][{alert_type}] {json.dumps(payload)}"

    send_slack_alert(
        {
            "text": f"TrailMetrics {severity_upper} alert: {alert_type}",
            "attachments": [
                {
                    "color": SEVERITY_COLORS.get(severity, SEVERITY_COLORS["warning"]),
                    "fields": [
                        {"title": "Type", "value": alert_type, "short": True},
                        {"title": "Severity", "value": severity_upper, "short": True},
                        {"title": "Details", "value": json.dumps(payload), "short": False},
                    ],
                    "footer": f"Dedup cooldown: {cooldown}s",
                }
            ],
        }
    )
    send_email_alert(f"TrailMetrics {severity_upper} Alert: {alert_type}", message)
    _store_alert_event(alert_type, severity, payload, key)

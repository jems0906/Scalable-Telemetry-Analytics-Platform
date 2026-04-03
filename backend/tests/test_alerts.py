import fakeredis

from app.services import alerts


def test_emit_alert_deduplicates_within_cooldown(monkeypatch) -> None:
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(alerts, "redis_client", fake_redis)
    monkeypatch.setattr(alerts.settings, "alert_dedup_cooldown_seconds", 120)

    sent = {"slack": 0, "email": 0}

    def fake_slack(_: dict) -> None:
        sent["slack"] += 1

    def fake_email(_: str, __: str) -> None:
        sent["email"] += 1

    monkeypatch.setattr(alerts, "send_slack_alert", fake_slack)
    monkeypatch.setattr(alerts, "send_email_alert", fake_email)

    payload = {"service_name": "checkout-service", "error_rate": 0.05, "p99_latency_ms": 720}
    dedup_key = "alert:dedup:SLO_BREACH:checkout-service:critical"

    alerts.emit_alert("SLO_BREACH", payload, severity="critical", dedup_key=dedup_key)
    alerts.emit_alert("SLO_BREACH", payload, severity="critical", dedup_key=dedup_key)

    assert sent["slack"] == 1
    assert sent["email"] == 1

    history = alerts.fetch_alert_history(limit=10)
    assert len(history) == 1
    assert history[0]["type"] == "SLO_BREACH"
    assert history[0]["severity"] == "critical"


def test_fetch_alert_history_honors_limit(monkeypatch) -> None:
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(alerts, "redis_client", fake_redis)
    monkeypatch.setattr(alerts.settings, "alert_dedup_cooldown_seconds", 1)
    monkeypatch.setattr(alerts, "send_slack_alert", lambda _: None)
    monkeypatch.setattr(alerts, "send_email_alert", lambda _a, _b: None)

    for i in range(3):
        alerts.emit_alert(
            "SLO_BREACH",
            {"service_name": f"svc-{i}", "error_rate": 0.01 + i, "p99_latency_ms": 300 + i},
            severity="warning",
            dedup_key=f"alert:dedup:SLO_BREACH:svc-{i}:warning",
        )

    history = alerts.fetch_alert_history(limit=2)
    assert len(history) == 2

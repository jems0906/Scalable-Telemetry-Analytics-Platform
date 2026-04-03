from app.services.slo import classify_slo_severity


def test_classify_slo_severity_warning() -> None:
    assert classify_slo_severity(520, 0.01) == "warning"


def test_classify_slo_severity_major() -> None:
    assert classify_slo_severity(760, 0.01) == "major"


def test_classify_slo_severity_critical() -> None:
    assert classify_slo_severity(1200, 0.03) == "critical"

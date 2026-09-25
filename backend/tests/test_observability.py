"""Health + Prometheus metrics endpoints."""

from __future__ import annotations


def test_health_reports_status_version_engine(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data["version"], str) and data["version"]
    assert data["engine"] in ("local", "azure")


def test_metrics_exposes_spiik_series(client):
    res = client.get("/api/languages")
    assert res.status_code == 200
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    body = res.text
    for series in (
        "spiik_http_requests_total",
        "spiik_http_request_duration_seconds_bucket",
        "spiik_http_requests_in_flight",
        "spiik_build_info",
    ):
        assert series in body, f"missing series {series}"


def test_metrics_counts_requests_but_not_itself(client):
    # the prometheus registry is process-global, so earlier tests may
    # already have hit /api/languages — assert a positive count, not 1
    client.get("/api/languages")
    body = client.get("/metrics").text
    languages_line = next(
        line
        for line in body.splitlines()
        if line.startswith("spiik_http_requests_total")
        and 'route="/api/languages"' in line
    )
    assert float(languages_line.rsplit(" ", 1)[1]) >= 1
    assert 'route="/metrics"' not in body


def test_assess_rejects_empty_upload(client):
    res = client.post("/api/assess")
    assert res.status_code in (422, 400)

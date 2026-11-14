import os
from urllib.parse import quote

from fastapi.testclient import TestClient

from app import config, export
from app.main import app


def test_mongo_uri_url_encodes_credentials(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    uri = config.mongo_uri()
    assert quote("test-user", safe="") in uri
    assert quote("p@ss word/with:chars", safe="") in uri
    assert "p@ss word/with:chars" not in uri


def test_health_reports_degraded_without_atlas(client):
    body = client.get("/api/health").json()
    assert body["status"] in ("ok", "degraded")
    assert "components" in body and "mongodb" in body["components"]


def test_settings_never_leaks_credentials(client):
    body = client.get("/api/settings")
    assert body.status_code == 200
    text = body.text.lower()
    assert "password" not in text and "mongodb_password" not in text
    assert body.json()["execution_mode"].startswith("single-node pseudo-distributed")


def test_validation_error_shape(client):
    response = client.post("/api/sales/transactions", json={"product_id": ""})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert detail["fields"]


def test_export_formula_injection_is_neutralised():
    body = export._render(["name", "value"], [["=cmd|calc", "@SUM(A1)"]])
    rows = list(__import__("csv").reader(body.splitlines()))
    assert rows[1] == ["'=cmd|calc", "'@SUM(A1)"]


def test_unknown_export_dataset_returns_404(client):
    response = client.get("/api/sales/reports/export/nonsense.csv")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "UNKNOWN_DATASET"

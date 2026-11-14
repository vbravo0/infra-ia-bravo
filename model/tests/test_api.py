"""Tests de integracion y contrato de la API en ambiente aislado."""

from fastapi.testclient import TestClient
from serve import app

client = TestClient(app)


def test_healthz():
    """Verifica que el probe de salud responda 200 con version y hash de prompt."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "prompt_hash" in data


def test_predict_tfidf():
    """Prueba prediccion con modelo supervisado: debe incluir confidence float y model_hash."""
    payload = {
        "cve_id": "CVE-TEST-001",
        "description": "Buffer overflow in network daemon allows remote root execution",
        "engine": "tfidf",
    }
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(data["confidence"], float)
    assert data["model_hash"] == "test-sha"


def test_feedback_append_only():
    """Prueba que el feedback registre un evento nuevo sin sobreescribir la tabla history."""
    # 1. Crear una prediccion previa
    client.post(
        "/predict", json={"cve_id": "CVE-TEST-002", "description": "SQL injection"}
    )

    # 2. Enviar primer feedback humano
    fb1 = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "HIGH"}
    )
    assert fb1.status_code == 200
    id1 = fb1.json()["feedback_id"]

    # 3. Enviar segundo feedback corregido (debe dar nuevo ID, no UPDATE)
    fb2 = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "CRITICAL"}
    )
    assert fb2.status_code == 200
    id2 = fb2.json()["feedback_id"]

    assert id2 > id1, "El feedback debe ser append-only con IDs incrementales"


def test_feedback_invalid_class():
    """Verifica que rechace severidades invalidas con HTTP 400."""
    res = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-003", "actual_severity": "SUPER_GRAVE"}
    )
    assert res.status_code == 400

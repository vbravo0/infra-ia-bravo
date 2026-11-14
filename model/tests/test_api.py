"""Tests de integracion y contrato de la API en ambiente aislado."""

import pytest
from fastapi.testclient import TestClient
from domain.predictor import FakePredictor
from serve import create_app


@pytest.fixture
def client():
    """Application Factory fixture: entrega una instancia limpia de la app por test."""
    app = create_app()
    return TestClient(app)


def test_healthz(client: TestClient):
    """Verifica que el probe de salud responda 200 con version y hash de prompt."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "prompt_hash" in data


def test_predict_tfidf(client: TestClient):
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


def test_predict_llm_with_fake():
    """Prueba prediccion LLM inyectando FakePredictor en una instancia nueva de la app."""
    fake_llm = FakePredictor(
        severity="CRITICAL", confidence=None, raw_output='{"severity":"CRITICAL"}'
    )
    # Instancia de app aislada con sus propios predictores
    custom_app = create_app(predictors={"llm": fake_llm})
    test_client = TestClient(custom_app)

    payload = {
        "cve_id": "CVE-TEST-LLM",
        "description": "Remote code execution via deserialization",
        "engine": "llm",
    }
    res = test_client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["severity"] == "CRITICAL"
    assert data["confidence"] is None
    assert len(fake_llm.calls) == 1


def test_feedback_append_only():
    """Prueba feedback e IDs incrementales usando una instancia de app con predictor controlado."""
    # Instancia aislada con tfidf seteado en LOW
    fake_tfidf = FakePredictor(severity="LOW", confidence=0.88)
    custom_app = create_app(predictors={"tfidf": fake_tfidf})
    test_client = TestClient(custom_app)

    pred_res = test_client.post(
        "/predict",
        json={
            "cve_id": "CVE-TEST-002",
            "description": "SQL injection in auth header",
            "engine": "tfidf",
        },
    )
    assert pred_res.status_code == 200
    assert pred_res.json()["severity"] == "LOW"

    # Enviar primer feedback humano discrepante (CRITICAL vs LOW original)
    fb1 = test_client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "CRITICAL"}
    )
    assert fb1.status_code == 200
    id1 = fb1.json()["feedback_id"]

    # Enviar segundo feedback corregido (debe dar nuevo ID, no UPDATE)
    fb2 = test_client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "HIGH"}
    )
    assert fb2.status_code == 200
    id2 = fb2.json()["feedback_id"]

    assert id2 > id1, "El feedback debe ser append-only con IDs incrementales"


def test_feedback_invalid_class(client: TestClient):
    """Verifica que rechace severidades invalidas con HTTP 400."""
    res = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-003", "actual_severity": "SUPER_GRAVE"}
    )
    assert res.status_code == 400

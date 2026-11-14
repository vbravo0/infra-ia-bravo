"""Tests de integracion y contrato de la API en ambiente aislado."""

from fastapi.testclient import TestClient
from domain.predictor import FakePredictor
from domain.service import register_predictor
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


def test_predict_llm_with_fake():
    """Prueba contrato de prediccion LLM inyectando FakePredictor sin requerir GPU ni Ollama."""
    fake_llm = FakePredictor(
        severity="CRITICAL", confidence=None, raw_output='{"severity":"CRITICAL"}'
    )
    register_predictor("llm", fake_llm)

    payload = {
        "cve_id": "CVE-TEST-LLM",
        "description": "Remote code execution via deserialization",
        "engine": "llm",
    }
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["severity"] == "CRITICAL"
    assert data["confidence"] is None
    assert len(fake_llm.calls) == 1


def test_feedback_append_only():
    """Prueba que el feedback registre eventos nuevos e IDs incrementales con prediccion controlada."""
    # 1. Inyectar predictor fake para controlar la severidad original exactamente en LOW
    fake_engine = FakePredictor(severity="LOW", confidence=0.88)
    register_predictor("fake_engine", fake_engine)

    pred_res = client.post(
        "/predict",
        json={
            "cve_id": "CVE-TEST-002",
            "description": "SQL injection in auth header",
            "engine": "fake_engine",
        },
    )
    assert pred_res.status_code == 200
    assert pred_res.json()["severity"] == "LOW"

    # 2. Enviar primer feedback humano discrepante (CRITICAL vs LOW original)
    fb1 = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "CRITICAL"}
    )
    assert fb1.status_code == 200
    id1 = fb1.json()["feedback_id"]

    # 3. Enviar segundo feedback corregido (debe dar nuevo ID, no UPDATE)
    fb2 = client.post(
        "/feedback", json={"cve_id": "CVE-TEST-002", "actual_severity": "HIGH"}
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

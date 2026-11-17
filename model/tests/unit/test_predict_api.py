"""Tests unitarios del endpoint POST /predict (clasificacion individual, batch y validaciones)."""

import pytest  # type: ignore
from fastapi.testclient import TestClient
from domain.predictor import FakePredictor
from domain.repository import FakeCveRepository
from serve import create_app


@pytest.fixture
def client():
    """Application Factory fixture: entrega una instancia limpia con FakeCveRepository."""
    app = create_app(repo=FakeCveRepository())
    return TestClient(app)


def test_predict_tfidf(client: TestClient):
    """Prueba prediccion con modelo supervisado: debe incluir confidence float y model_hash."""
    payload = [
        {
            "cve_id": "CVE-TEST-001",
            "description": "Buffer overflow in network daemon allows remote root execution",
            "engine": "tfidf",
        }
    ]
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(data[0]["confidence"], float)
    assert data[0]["model_hash"] == "test-sha"


def test_predict_batch_list_success(client: TestClient):
    """Prueba que /predict acepte una lista y retorne la lista de resultados correspondientes."""
    payload = [
        {
            "cve_id": f"CVE-BATCH-{i:03d}",
            "description": f"Buffer overflow flaw {i}",
            "engine": "tfidf",
        }
        for i in range(1, 4)
    ]
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["cve_id"] == "CVE-BATCH-001"


def test_predict_batch_empty_list_returns_empty_list(client: TestClient):
    """Verifica que una lista vacia retorne lista vacia []."""
    res = client.post("/predict", json=[])
    assert res.status_code == 200
    assert res.json() == []


def test_predict_batch_rejects_more_than_50_items(client: TestClient):
    """Verifica que rechace con HTTP 400 si la lista excede el limite estricto de 50 CVEs."""
    payload = [
        {"cve_id": f"CVE-51-{i}", "description": "XSS attack", "engine": "tfidf"}
        for i in range(51)
    ]
    res = client.post("/predict", json=payload)
    assert res.status_code == 400
    assert "50" in res.json()["detail"]


def test_predict_llm_with_fake():
    """Prueba prediccion LLM inyectando FakePredictor en una instancia nueva de la app."""
    fake_llm = FakePredictor(
        severity="CRITICAL", confidence=None, raw_output='{"severity":"CRITICAL"}'
    )
    custom_app = create_app(predictors={"llm": fake_llm}, repo=FakeCveRepository())
    test_client = TestClient(custom_app)

    payload = [
        {
            "cve_id": "CVE-TEST-LLM",
            "description": "Remote code execution via deserialization",
            "engine": "llm",
        }
    ]
    res = test_client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data[0]["severity"] == "CRITICAL"
    assert data[0]["confidence"] is None
    assert len(fake_llm.calls) == 1


def test_predict_records_parse_error_in_repo():
    """Prueba que si el predictor marca parse_error=True, la API persista parse_error=1 en el repo."""
    broken_llm = FakePredictor(
        severity="UNKNOWN",
        confidence=None,
        parse_error=True,
        raw_output="HACKED_SYSTEM_OVERRIDE",
    )
    fake_repo = FakeCveRepository()
    app = create_app(predictors={"llm": broken_llm}, repo=fake_repo)
    test_client = TestClient(app)

    res = test_client.post(
        "/predict",
        json=[
            {
                "cve_id": "CVE-PARSE-ERR-001",
                "description": "Arbitrary vulnerability text",
                "engine": "llm",
            }
        ],
    )
    assert res.status_code == 200
    data = res.json()
    assert data[0]["severity"] == "UNKNOWN"
    assert data[0]["parse_error"] is True
    assert data[0]["raw_llm"] == "HACKED_SYSTEM_OVERRIDE"
    assert len(fake_repo.history) == 1
    assert fake_repo.history[0]["parse_error"] == 1
    assert fake_repo.history[0]["severity"] == "UNKNOWN"

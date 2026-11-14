"""Servicio de dominio para clasificacion de severidad de CVEs."""

import time
from typing import Mapping

from domain.predictor import OllamaPredictor, SeverityPredictor, TfidfPredictor
from domain.repository import CveRepository
from domain.schemas import PredictRequest, PredictResult


def default_predictors() -> dict[str, SeverityPredictor]:
    """Crea el conjunto de predictores estandar de produccion."""
    prompt_text, _ = load_prompt()
    return {
        "tfidf": TfidfPredictor(),
        "llm": OllamaPredictor(prompt_text=prompt_text),
    }


async def classify_cve(
    req: PredictRequest,
    predictors: Mapping[str, SeverityPredictor],
    repo: CveRepository,
) -> PredictResult:
    """Clasifica la severidad de un CVE usando el motor provisto y persiste via CveRepository.

    Args:
        req: Objeto PredictRequest con cve_id, description y engine.
        predictors: Mapeo inmutable de motores registrados.
        repo: Implementacion del trait CveRepository para persistencia.

    Returns:
        Objeto PredictResult con la prediccion, modelo, latencia y persistencia.
    """
    if req.engine not in predictors:
        raise ValueError(f"Motor no configurado: {req.engine}")

    start = time.perf_counter()
    _, prompt_hash = load_prompt()

    predictor = predictors[req.engine]
    severity, conf, parse_error, raw_llm = await predictor.predict(req.description)

    if parse_error:
        INVALID_OUTPUT.labels(version=MODEL_VERSION, prompt_hash=prompt_hash).inc()

    elapsed = time.perf_counter() - start
    res = PredictResult(
        cve_id=req.cve_id,
        engine=req.engine,
        severity=severity,
        model_hash=MODEL_VERSION,
        confidence=conf,
        parse_error=parse_error,
        raw_llm=raw_llm,
        model_version=MODEL_VERSION,
        prompt_hash=prompt_hash,
        latency_ms=round(elapsed * 1000, 2),
    )
    PREDICTIONS.labels(
        engine=req.engine,
        severity=severity,
        version=MODEL_VERSION,
        prompt_hash=prompt_hash,
    ).inc()
    PREDICT_LATENCY.labels(engine=req.engine).observe(elapsed)
    repo.save_prediction(res, req.description)
    return res

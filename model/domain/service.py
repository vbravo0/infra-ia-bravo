"""Servicio de dominio para clasificacion de severidad de CVEs."""

import time
from typing import Optional

from adapters.metrics import INVALID_OUTPUT, PREDICT_LATENCY, PREDICTIONS
from adapters.postgres_repo import save_prediction
from adapters.prompt_repo import load_prompt
from config import MODEL_VERSION
from domain.predictor import OllamaPredictor, SeverityPredictor, TfidfPredictor
from domain.schemas import PredictRequest, PredictResult

# Registro de motores de inferencia desacoplados (inversion de dependencias simple)
_PREDICTORS: dict[str, SeverityPredictor] = {
    "tfidf": TfidfPredictor(),
}


def register_predictor(engine: str, predictor: SeverityPredictor) -> None:
    """Registra o reemplaza un motor de inferencia (util para testing o extension).

    Args:
        engine: Nombre del motor ('tfidf', 'llm', 'fake', etc).
        predictor: Objeto que cumple el trait SeverityPredictor.
    """
    _PREDICTORS[engine] = predictor


def get_predictor(engine: str, prompt_text: str = "") -> SeverityPredictor:
    """Obtiene el predictor registrado o instancia el default segun el motor."""
    if engine in _PREDICTORS:
        return _PREDICTORS[engine]
    if engine == "llm":
        return OllamaPredictor(prompt_text=prompt_text)
    raise ValueError(f"Motor desconocido: {engine}")


async def classify_cve(req: PredictRequest) -> PredictResult:
    """Clasifica la severidad de un CVE usando el motor especificado.

    Args:
        req: Objeto PredictRequest con cve_id, description y engine.

    Returns:
        Objeto PredictResult con la prediccion, modelo, latencia y persistencia.
    """
    start = time.perf_counter()
    prompt_text, prompt_hash = load_prompt()

    predictor = get_predictor(req.engine, prompt_text=prompt_text)
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
    save_prediction(res, req.description)
    return res

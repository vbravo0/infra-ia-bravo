import time

from adapters.metrics import INVALID_OUTPUT, PREDICT_LATENCY, PREDICTIONS
from adapters.ml_classifier import is_ready, predict_tfidf
from adapters.ollama_client import predict_llm
from adapters.prompt_repo import load_prompt
from adapters.postgres_repo import save_prediction
from config import MODEL_VERSION
from domain.schemas import PredictRequest, PredictResult


async def classify_cve(req: PredictRequest) -> PredictResult:
    if not is_ready():
        raise RuntimeError("model not loaded yet")

    start = time.perf_counter()
    prompt_text, prompt_hash = load_prompt()
    parse_error = False
    raw_llm = ""

    if req.engine == "llm":
        severity, conf, parse_error, raw_llm = await predict_llm(
            prompt_text, req.description
        )
        if parse_error:
            INVALID_OUTPUT.labels(version=MODEL_VERSION, prompt_hash=prompt_hash).inc()
    else:
        severity, conf = predict_tfidf(req.description)

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

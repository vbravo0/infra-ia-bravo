from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from adapters.ml_classifier import is_ready
from adapters.prompt_repo import load_prompt
from adapters.postgres_repo import list_history, update_feedback
from adapters.metrics import FEEDBACK_TOTAL, FEEDBACK_DISCREPANCY
from config import MODEL_VERSION, PROMPT_PATH, TEMPLATE_PATH, VALID_CLASSES
from domain.schemas import PredictRequest, FeedbackRequest, FeedbackResult
from domain.service import classify_cve

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def ui() -> str:
    """Renderiza la interfaz web minima de prueba del pod."""
    prompt_text, prompt_hash = load_prompt()
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        html.replace("{{MODEL_VERSION}}", MODEL_VERSION)
        .replace("{{PROMPT_HASH}}", prompt_hash)
        .replace("{{PROMPT_TEXT}}", prompt_text)
    )


@router.get("/healthz")
def healthz() -> Response:
    """Probe de readiness/liveness para Kubernetes."""
    if not is_ready() or not PROMPT_PATH.exists():
        return Response(
            content='{"status":"loading"}',
            status_code=503,
            media_type="application/json",
        )
    _, prompt_hash = load_prompt()
    return Response(
        content=f'{{"status":"ok","model_version":"{MODEL_VERSION}","prompt_hash":"{prompt_hash}"}}',
        media_type="application/json",
    )


@router.get("/metrics")
def metrics() -> Response:
    """Endpoint de scraping para Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/predict")
async def predict(req: PredictRequest):
    """Clasifica una vulnerabilidad usando el motor solicitado (tfidf o llm)."""
    try:
        return await classify_cve(req)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/history")
def history():
    """Retorna las ultimas inferencias registradas en la base de datos."""
    return list_history()


@router.post("/feedback", response_model=FeedbackResult)
def feedback(req: FeedbackRequest):
    """Recibe la severidad real (de NVD o del analista) y actualiza el registro."""
    actual = req.actual_severity.strip().upper()
    if actual not in VALID_CLASSES:
        raise HTTPException(
            400,
            f"actual_severity invalida: {req.actual_severity}. Clases validas: {VALID_CLASSES}",
        )

    updated_rows = update_feedback(req.cve_id, actual)
    if not updated_rows:
        raise HTTPException(404, f"No se encontro prediccion previa para {req.cve_id}")

    FEEDBACK_TOTAL.labels(actual_severity=actual).inc()
    for row in updated_rows:
        pred_sev = row.get("severity", "UNKNOWN")
        engine = row.get("engine", "unknown")
        if pred_sev != actual:
            FEEDBACK_DISCREPANCY.labels(
                engine=engine, pred_severity=pred_sev, actual_severity=actual
            ).inc()

    return FeedbackResult(
        status="ok",
        cve_id=req.cve_id,
        actual_severity=actual,
        rows_updated=len(updated_rows),
    )

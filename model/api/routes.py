from typing import Union
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from adapters.ml_classifier import is_ready
from adapters.prompt_repo import load_prompt
from adapters.metrics import FEEDBACK_TOTAL, FEEDBACK_DISCREPANCY
from config import MODEL_VERSION, PROMPT_PATH, TEMPLATE_PATH, VALID_CLASSES
from domain.repository import CveRepository
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
async def predict(
    payload: Union[PredictRequest, list[PredictRequest]], request: Request
):
    """Clasifica vulnerabilidades (acepta un unico CVE o lista de hasta 50).

    - Si recibe un unico objeto PredictRequest: devuelve un PredictResult.
    - Si recibe una lista []: devuelve [] (si esta vacia) o list[PredictResult] (hasta 50).
    - Si la lista excede 50 items: rechaza con HTTP 400.
    """
    predictors = request.app.state.predictors
    repo: CveRepository = request.app.state.repo

    if isinstance(payload, list):
        if len(payload) > 50:
            raise HTTPException(
                400,
                f"Excede el limite maximo de 50 CVEs por request (recibidos: {len(payload)})",
            )
        if len(payload) == 0:
            return []

        results: list[PredictResult] = []
        for item in payload:
            try:
                res = await classify_cve(item, predictors, repo)
                results.append(res)
            except (RuntimeError, ValueError) as exc:
                raise HTTPException(503, str(exc)) from exc
        return results

    # Caso de un unico objeto PredictRequest
    try:
        return await classify_cve(payload, predictors, repo)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/history")
def history(request: Request):
    """Retorna las ultimas inferencias registradas en la base de datos."""
    repo: CveRepository = request.app.state.repo
    return repo.list_history()


def _record_discrepancy_metrics(cve_id: str, actual: str, repo: CveRepository) -> None:
    """Contrasta la severidad real con predicciones previas y actualiza metricas Prometheus."""
    predictions = repo.get_predictions_for_cve(cve_id)
    FEEDBACK_TOTAL.labels(actual_severity=actual).inc()
    for row in predictions:
        pred_sev = row.get("severity", "UNKNOWN")
        engine = row.get("engine", "unknown")
        if pred_sev != actual:
            FEEDBACK_DISCREPANCY.labels(
                engine=engine, pred_severity=pred_sev, actual_severity=actual
            ).inc()


@router.post("/feedback", response_model=FeedbackResult)
def feedback(req: FeedbackRequest, request: Request):
    """Registra la severidad real (de NVD o del analista) de forma inmutable (append-only)."""
    actual = req.actual_severity.strip().upper()
    if actual not in VALID_CLASSES:
        raise HTTPException(
            400,
            f"actual_severity invalida: {req.actual_severity}. Clases validas: {VALID_CLASSES}",
        )

    repo: CveRepository = request.app.state.repo
    feedback_id = repo.append_feedback(
        cve_id=req.cve_id,
        actual_severity=actual,
        source=req.source,
        notes=req.notes,
    )
    _record_discrepancy_metrics(req.cve_id, actual, repo)

    return FeedbackResult(
        status="ok",
        feedback_id=feedback_id,
        cve_id=req.cve_id,
        actual_severity=actual,
        source=req.source,
    )

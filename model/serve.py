"""Servidor API HTTP para clasificacion de severidad de CVEs."""

from typing import Optional, Mapping
from fastapi import FastAPI
import uvicorn

from adapters.ml_classifier import load_model
from adapters.postgres_repo import PostgresCveRepository
from api.routes import router
from config import MODEL_VERSION, PORT
from domain.predictor import SeverityPredictor
from domain.repository import CveRepository
from domain.service import default_predictors

# Carga bloqueante síncrona: si los pesos no existen o estan corruptos,
# el proceso falla inmediatamente (fail-fast) sin abrir el puerto.
load_model()


def create_app(
    predictors: Optional[Mapping[str, SeverityPredictor]] = None,
    repo: Optional[CveRepository] = None,
) -> FastAPI:
    """Application factory inmutable: inyecta predictores y repositorio sin estado global."""
    app = FastAPI(title="cve-model-server", version=MODEL_VERSION)
    app.state.predictors = (
        default_predictors() if predictors is None else dict(predictors)
    )
    app.state.repo = PostgresCveRepository() if repo is None else repo
    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

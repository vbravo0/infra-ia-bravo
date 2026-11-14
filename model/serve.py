"""Servidor API HTTP para clasificacion de severidad de CVEs."""

from fastapi import FastAPI
import uvicorn

from adapters.ml_classifier import load_model
from api.routes import router
from config import MODEL_VERSION, PORT

# Carga bloqueante síncrona: si los pesos no existen o estan corruptos,
# el proceso falla inmediatamente (fail-fast) sin abrir el puerto.
load_model()


def create_app() -> FastAPI:
    """Application factory: crea y configura la instancia de FastAPI."""
    app = FastAPI(title="cve-model-server", version=MODEL_VERSION)
    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

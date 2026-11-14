from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from adapters.ml_classifier import load_model
from api.routes import router
from config import MODEL_VERSION, PORT


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        load_model()
    except Exception as exc:
        print(f"model not loaded: {exc}", flush=True)
    yield


app = FastAPI(title="cve-model-server", version=MODEL_VERSION, lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

import joblib
from config import GCS_BUCKET, MODEL_BLOB_PATH, MODEL_PATH

_bundle = None


def _download_from_gcs_if_configured() -> None:
    """Descarga el artefacto binario desde Cloud Storage si GCS_BUCKET esta definido."""
    if not GCS_BUCKET or MODEL_PATH.exists():
        return

    from google.cloud import storage

    blob_path = MODEL_BLOB_PATH or "model.joblib"
    print(f"Descargando modelo desde gs://{GCS_BUCKET}/{blob_path} a {MODEL_PATH}...")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_path)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(MODEL_PATH))
    print("Descarga de modelo finalizada con exito.")


def load_model() -> None:
    global _bundle
    if _bundle is None:
        _download_from_gcs_if_configured()
        _bundle = joblib.load(MODEL_PATH)


def is_ready() -> bool:
    return _bundle is not None


def predict_tfidf(description: str) -> tuple[str, float]:
    if _bundle is None:
        raise RuntimeError("model not loaded yet")
    model = _bundle["model"]
    proba = model.predict_proba([description])[0]
    idx = int(proba.argmax())
    return str(model.classes_[idx]), round(float(proba[idx]), 3)

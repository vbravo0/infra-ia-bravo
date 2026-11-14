import joblib
from config import MODEL_PATH

_bundle = None


def load_model() -> None:
    global _bundle
    if _bundle is None:
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

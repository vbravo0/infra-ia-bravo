"""Entrena el modelo propio de CVE (TF-IDF + LogisticRegression) y registra su versionado."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

DATA_PATH = "data/sample_1000.csv"
MODELS_DIR = Path("models")


def get_git_commit() -> str:
    """Obtiene el hash del commit actual o fallback a variable de entorno."""
    env_sha = os.environ.get("MODEL_VERSION")
    if env_sha and env_sha != "local":
        return env_sha
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "unknown"


def clean_cve_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el DataFrame de entrenamiento segun los criterios de calidad:

    Precondicion:
        - El DataFrame contiene las columnas 'DESCRIPTION' y 'SEVERITY'.
    """
    cleaned = df.dropna(subset=["DESCRIPTION", "SEVERITY"])
    return cleaned.drop_duplicates(subset=["DESCRIPTION"])


def main() -> None:
    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    target_dir = MODELS_DIR / version
    target_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    df = clean_cve_dataset(df)

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=3000, stop_words="english")),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=500)),
        ]
    )

    start_time = time.perf_counter()
    pipeline.fit(df["DESCRIPTION"], df["SEVERITY"])
    duration = time.perf_counter() - start_time

    y_pred = pipeline.predict(df["DESCRIPTION"])
    macro_f1 = float(f1_score(df["SEVERITY"], y_pred, average="macro", zero_division=0))
    acc = float(accuracy_score(df["SEVERITY"], y_pred))

    artifact = {"model": pipeline, "classes": list(pipeline.classes_)}
    joblib.dump(artifact, target_dir / "model.joblib")
    joblib.dump(artifact, "model.joblib")

    metadata = {
        "model_version": version,
        "git_commit": get_git_commit(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 3),
        "dataset_rows": len(df),
        "metrics": {"macro_f1": round(macro_f1, 4), "accuracy": round(acc, 4)},
    }

    with open(target_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(
        f"Modelo entrenado en {duration:.2f}s -> {target_dir}/ ({len(df)} filas, F1={macro_f1:.4f})"
    )


if __name__ == "__main__":
    main()

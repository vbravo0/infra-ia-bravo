"""Entrena el modelo propio de CVE (TF-IDF + LogisticRegression) en BUILD TIME
(adentro de la imagen Docker), siguiendo el patron exacto de model/train.py del curso.
"""

from __future__ import annotations

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

MODEL_PATH = "model.joblib"
DATA_PATH = "sample_500.csv"


def clean_cve_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el DataFrame de entrenamiento segun los criterios de calidad:

    - Descarta filas con nulos en 'DESCRIPTION' o 'SEVERITY' (dropna).
    - Descarta registros con descripciones duplicadas (drop_duplicates).
    """
    cleaned = df.dropna(subset=["DESCRIPTION", "SEVERITY"])
    cleaned = cleaned.drop_duplicates(subset=["DESCRIPTION"])
    return cleaned


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df = clean_cve_dataset(df)

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=3000, stop_words="english")),
            (
                "clf",
                LogisticRegression(class_weight="balanced", max_iter=500),
            ),
        ]
    )
    pipeline.fit(df["DESCRIPTION"], df["SEVERITY"])
    joblib.dump({"model": pipeline, "classes": list(pipeline.classes_)}, MODEL_PATH)
    print(f"Modelo CVE entrenado ({len(df)} filas) -> {MODEL_PATH}")


if __name__ == "__main__":
    main()

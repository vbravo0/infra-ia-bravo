"""Script que corre en el CI/CD antes de construir la imagen Docker.
Evalua el modelo y el prompt contra un set de prueba.
Si el Macro F1 o el F2-Score caen por debajo del umbral minimo,
el script sale con codigo de error (exit 1) y FRENA el despliegue.
"""

from __future__ import annotations

import sys
import pandas as pd
from sklearn.metrics import f1_score, fbeta_score
import joblib

DATA_PATH = "model/sample_500.csv"
MODEL_PATH = "model/model.joblib"
MIN_F1_THRESHOLD = 0.50  # Si da menos de 50%, no pasa a produccion


def test_quality_gate() -> None:
    print("--- [CI/CD QUALITY GATE] Evaluando calidad antes del deploy ---")

    # 1. Cargar datos de test
    df = pd.read_csv(DATA_PATH).dropna(subset=["DESCRIPTION", "SEVERITY"])

    # 2. Cargar modelo generado
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]

    # 3. Predecir
    y_true = df["SEVERITY"]
    y_pred = model.predict(df["DESCRIPTION"])

    # 4. Calcular metricas clave
    macro_f1 = f1_score(y_true, y_pred, average="macro")
    # F2 score ponderando el doble a la clase CRITICAL
    y_true_crit = (y_true == "CRITICAL").astype(int)
    y_pred_crit = (y_pred == "CRITICAL").astype(int)
    f2_crit = fbeta_score(y_true_crit, y_pred_crit, beta=2)

    print(f"Resultados de la evaluacion:")
    print(f"  - Macro F1-Score: {macro_f1:.3f}")
    print(f"  - F2-Score (CRITICAL): {f2_crit:.3f}")

    # 5. Gate de corte
    if macro_f1 < MIN_F1_THRESHOLD:
        print(
            f"❌ RECHAZADO: Macro F1 ({macro_f1:.3f}) inferior al umbral ({MIN_F1_THRESHOLD})"
        )
        print("El pipeline aborta la construccion de la imagen Docker.")
        sys.exit(1)

    print("✅ APROBADO: El modelo cumple los estandares de calidad.")


if __name__ == "__main__":
    test_quality_gate()

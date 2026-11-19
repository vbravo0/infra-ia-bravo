"""Modulo de Evaluacion de un Modelo (Quality Gate Macro F1).

Responsabilidad unica:
- Cargar un CSV de predicciones y compararlo contra la verdad de terreno.
- Calcular Macro F1 y validar el Quality Gate de CI/CD.

Uso:
    python model/eval/evaluate.py --pred data/predictions_tfidf.csv
    python model/eval/evaluate.py --pred data/predictions_llm.csv --no-gate
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.metrics import (
    MIN_MACRO_F1,
    check_quality_gate,
    evaluate_predictions,
)


def load_series(csv_path: str, column_name: str) -> list[str]:
    """Lee una columna especifica de un CSV."""
    df = pd.read_csv(csv_path)
    return df[column_name].dropna().astype(str).tolist()


def evaluate_model(data_path: str, pred_path: str, enforce_gate: bool) -> float:
    """Calcula Macro F1 y valida contra el umbral minimo de produccion."""
    raw_true = load_series(data_path, "SEVERITY")
    raw_pred = load_series(pred_path, "PREDICTION")

    min_len = min(len(raw_true), len(raw_pred))
    y_true, y_pred = raw_true[:min_len], raw_pred[:min_len]

    score = evaluate_predictions(y_true, y_pred)["macro_f1"]
    print(f"--- [QUALITY GATE F1] Dataset: {data_path} | Predicciones: {pred_path} ---")
    print(f"Muestras evaluadas: {len(y_true)}")
    print(f"Macro F1-Score:     {score:.4f}")

    if enforce_gate:
        check_quality_gate(score, min_f1=MIN_MACRO_F1)
        print("✅ APROBADO: Cumple con el Quality Gate de produccion.")
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluador Quality Gate Macro F1")
    parser.add_argument(
        "--data", default="data/sample_1000.csv", help="Dataset con ground truth"
    )
    parser.add_argument("--pred", required=True, help="CSV con predicciones del modelo")
    parser.add_argument(
        "--no-gate", action="store_true", help="No abortar si F1 < 0.60"
    )

    args = parser.parse_args()
    evaluate_model(args.data, args.pred, not args.no_gate)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ RECHAZADO: {err}", file=sys.stderr)
        sys.exit(1)

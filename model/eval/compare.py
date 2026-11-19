"""Modulo de Comparacion Estadistica entre Modelos (REQ-09).

Responsabilidad unica:
- Comparar las predicciones de dos modelos sobre el mismo dataset.
- Calcular Test de McNemar (significancia de discordancias).
- Calcular Bootstrap pareado (intervalo de confianza al 95% para la mejora de Macro F1).

Uso:
    python model/eval/compare.py --pred-a data/predictions_a.csv --pred-b data/predictions_b.csv
    python model/eval/compare.py --pred-a data/predictions_a.csv --pred-b data/predictions_b.csv --metric mcnemar
    python model/eval/compare.py --pred-a data/predictions_a.csv --pred-b data/predictions_b.csv --metric bootstrap
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.metrics import (
    evaluate_predictions,
    mcnemar_test,
    paired_bootstrap_macro_f1,
)


def load_series(csv_path: str, column_name: str) -> list[str]:
    """Lee una columna especifica de un CSV."""
    df = pd.read_csv(csv_path)
    return df[column_name].dropna().astype(str).tolist()


def compare_mcnemar(
    y_true: list[str], y_pred_a: list[str], y_pred_b: list[str]
) -> dict[str, float]:
    """Calcula el test de significancia de McNemar."""
    res = mcnemar_test(y_true, y_pred_a, y_pred_b)
    print("\n[Test de McNemar]")
    print(
        f"  Discordancias: A acierta y B falla = {res['b']} | A falla y B acierta = {res['c']}"
    )
    print(f"  Chi2 (Edwards): {res['statistic']:.4f}")
    print(f"  p-value:        {res['p_value']:.6f}")
    conclusion = (
        "Significativa (p < 0.05)"
        if res["p_value"] < 0.05
        else "No significativa (p >= 0.05)"
    )
    print(f"  Conclusion:     {conclusion}")
    return res


def compare_bootstrap(
    y_true: list[str], y_pred_a: list[str], y_pred_b: list[str]
) -> dict[str, float]:
    """Calcula el intervalo de confianza al 95% para la diferencia de Macro F1 (B - A)."""
    res = paired_bootstrap_macro_f1(y_true, y_pred_a, y_pred_b)
    print("\n[Bootstrap Pareado (Macro F1, 1000 iteraciones)]")
    print(f"  Delta promedio (B - A): {res['mean_delta']:+.4f}")
    print(f"  IC 95%:                [{res['ci_lower']:+.4f}, {res['ci_upper']:+.4f}]")
    print(f"  p-value empirico:       {res['p_value']:.6f}")
    return res


def compare_models(
    data_path: str, pred_a_path: str, pred_b_path: str, metric: str
) -> None:
    """Orquesta la comparacion estadistica de modelos."""
    raw_true = load_series(data_path, "SEVERITY")
    raw_a = load_series(pred_a_path, "PREDICTION")
    raw_b = load_series(pred_b_path, "PREDICTION")

    min_len = min(len(raw_true), len(raw_a), len(raw_b))
    y_true = raw_true[:min_len]
    y_a = raw_a[:min_len]
    y_b = raw_b[:min_len]

    f1_a = evaluate_predictions(y_true, y_a)["macro_f1"]
    f1_b = evaluate_predictions(y_true, y_b)["macro_f1"]

    print(f"--- [COMPARACION DE MODELOS] (Muestras: {min_len}) ---")
    print(f"Modelo A ({pred_a_path}): Macro F1 = {f1_a:.4f}")
    print(f"Modelo B ({pred_b_path}): Macro F1 = {f1_b:.4f}")

    if metric in ["mcnemar", "all"]:
        compare_mcnemar(y_true, y_a, y_b)

    if metric in ["bootstrap", "all"]:
        compare_bootstrap(y_true, y_a, y_b)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Comparador estadistico de modelos CVE"
    )
    parser.add_argument(
        "--data", default="data/sample_1000.csv", help="Dataset con ground truth"
    )
    parser.add_argument(
        "--pred-a", required=True, help="CSV de predicciones del Modelo A"
    )
    parser.add_argument(
        "--pred-b", required=True, help="CSV de predicciones del Modelo B"
    )
    parser.add_argument(
        "--metric",
        choices=["all", "mcnemar", "bootstrap"],
        default="all",
        help="Prueba a ejecutar: all, mcnemar o bootstrap (default: all)",
    )

    args = parser.parse_args()
    compare_models(args.data, args.pred_a, args.pred_b, args.metric)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ ERROR: {err}", file=sys.stderr)
        sys.exit(1)

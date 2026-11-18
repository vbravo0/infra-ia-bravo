"""Modulo de Evaluacion de Metricas y Significancia Estadistica (MLOps / LLMOps).

Consume predicciones (en memoria o desde CSV) y calcula metricas:
- F1-Score (Macro F1 y Quality Gate)
- McNemar (test de hipotesis entre dos modelos)
- Bootstrap pareado (intervalo de confianza al 95% para la diferencia de Macro F1)

Uso CLI:
    # 1. Evaluar Macro F1 de un modelo directo (para CI/CD Quality Gate)
    python model/eval/evaluate.py --metric f1 --model tfidf

    # 2. Evaluar Macro F1 desde un CSV de predicciones
    python model/eval/evaluate.py --metric f1 --pred data/predictions_tfidf.csv

    # 3. Comparar dos modelos con McNemar
    python model/eval/evaluate.py --metric mcnemar --pred-a data/predictions_v1.csv --pred-b data/predictions_v2.csv

    # 4. Comparar dos modelos con Bootstrap pareado (IC 95%)
    python model/eval/evaluate.py --metric bootstrap --pred-a data/predictions_v1.csv --pred-b data/predictions_v2.csv
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.adapters import EvaluatableModel, OllamaEvaluator, TfidfEvaluator
from eval.metrics import (
    MIN_MACRO_F1,
    check_quality_gate,
    evaluate_predictions,
    mcnemar_test,
    paired_bootstrap_macro_f1,
)


def load_ground_truth(data_path: str = "data/sample_1000.csv") -> list[str]:
    """Carga las etiquetas reales (SEVERITY) del dataset."""
    df = pd.read_csv(data_path).dropna(subset=["SEVERITY"])
    return df["SEVERITY"].tolist()


def load_predictions_from_csv(csv_path: str) -> list[str]:
    """Carga la columna de predicciones desde un archivo CSV."""
    df = pd.read_csv(csv_path)
    col = "PREDICTION" if "PREDICTION" in df.columns else df.columns[-1]
    return df[col].astype(str).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluador de metricas y estadistica CVE"
    )
    parser.add_argument(
        "--metric",
        choices=["f1", "mcnemar", "bootstrap", "all"],
        default="f1",
        help="Metrica o prueba estadistica a ejecutar (default: f1)",
    )
    parser.add_argument(
        "--data",
        default="data/sample_1000.csv",
        help="Dataset con la verdad de terreno (etiqueta real SEVERITY)",
    )
    # Evaluacion de un solo modelo (online / CI-CD)
    parser.add_argument(
        "--model",
        choices=["tfidf", "llm"],
        default=None,
        help="Ejecutar inferencia en memoria para el modelo indicado",
    )
    parser.add_argument(
        "--pred",
        default=None,
        help="Ruta al CSV con predicciones de un modelo para calcular F1",
    )
    # Comparacion entre dos modelos
    parser.add_argument(
        "--pred-a",
        default=None,
        help="Ruta al CSV de predicciones del Modelo A",
    )
    parser.add_argument(
        "--pred-b",
        default=None,
        help="Ruta al CSV de predicciones del Modelo B",
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="No lanzar error si Macro F1 < 0.60 (diagnostico)",
    )

    args = parser.parse_args()
    y_true = load_ground_truth(args.data)

    # ----------------------------------------------------
    # Caso 1: Evaluar F1 sobre un modelo (online o CSV)
    # ----------------------------------------------------
    if args.metric == "f1":
        if args.pred:
            y_pred = load_predictions_from_csv(args.pred)
        elif args.model == "tfidf":
            evaluator: EvaluatableModel = TfidfEvaluator()
            df = pd.read_csv(args.data)
            y_pred = evaluator.predict_batch(df["DESCRIPTION"].tolist())
        else:
            print(
                "❌ Error: Debes especificar --model tfidf o --pred <archivo.csv>",
                file=sys.stderr,
            )
            sys.exit(1)

        metrics = evaluate_predictions(y_true, y_pred)
        macro_f1 = metrics["macro_f1"]
        print(f"--- [EVALUACION F1] Dataset: {args.data} ---")
        print(f"Macro F1-Score: {macro_f1:.4f}")

        if not args.no_gate:
            check_quality_gate(macro_f1, min_f1=MIN_MACRO_F1)
            print("✅ APROBADO: Cumple con el Quality Gate de produccion.")
        return

    # ----------------------------------------------------
    # Caso 2: Comparar dos modelos (McNemar, Bootstrap o All)
    # ----------------------------------------------------
    if not args.pred_a or not args.pred_b:
        print(
            "❌ Error: Para pruebas comparativas debes proveer --pred-a y --pred-b.",
            file=sys.stderr,
        )
        sys.exit(1)

    y_pred_a = load_predictions_from_csv(args.pred_a)
    y_pred_b = load_predictions_from_csv(args.pred_b)

    if len(y_pred_a) != len(y_true) or len(y_pred_b) != len(y_true):
        print(
            f"❌ Error: La longitud de predicciones ({len(y_pred_a)}, {len(y_pred_b)}) no coincide con el dataset ({len(y_true)}).",
            file=sys.stderr,
        )
        sys.exit(1)

    f1_a = evaluate_predictions(y_true, y_pred_a)["macro_f1"]
    f1_b = evaluate_predictions(y_true, y_pred_b)["macro_f1"]

    print(f"--- [COMPARACION DE MODELOS] ---")
    print(f"Modelo A ({args.pred_a}): Macro F1 = {f1_a:.4f}")
    print(f"Modelo B ({args.pred_b}): Macro F1 = {f1_b:.4f}")

    if args.metric in ["mcnemar", "all"]:
        mc = mcnemar_test(y_true, y_pred_a, y_pred_b)
        print(f"\n[Test de McNemar]")
        print(
            f"  Discordancias: A acierta y B falla = {mc['b']} | A falla y B acierta = {mc['c']}"
        )
        print(f"  Chi2 (Edwards): {mc['statistic']:.4f}")
        print(f"  p-value:        {mc['p_value']:.6f}")
        sig = (
            "Significativa (p < 0.05)"
            if mc["p_value"] < 0.05
            else "No significativa (p >= 0.05)"
        )
        print(f"  Conclusion:     {sig}")

    if args.metric in ["bootstrap", "all"]:
        boot = paired_bootstrap_macro_f1(y_true, y_pred_a, y_pred_b)
        print(f"\n[Bootstrap Pareado (Macro F1, 1000 iteraciones)]")
        print(f"  Delta promedio (B - A): {boot['mean_delta']:+.4f}")
        print(
            f"  IC 95%:                [{boot['ci_lower']:+.4f}, {boot['ci_upper']:+.4f}]"
        )
        print(f"  p-value empirico:       {boot['p_value']:.6f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ RECHAZADO: {err}", file=sys.stderr)
        sys.exit(1)

"""Modulo de Evaluacion de Metricas y Significancia Estadistica (MLOps / LLMOps).

Estructura modular con funciones de evaluacion independientes:
- run_f1_evaluation: Calcula Macro F1 y valida Quality Gate.
- run_mcnemar_evaluation: Compara discordancias y significancia Chi2.
- run_bootstrap_evaluation: Estima intervalo de confianza al 95% para la mejora.
- run_comparative_evaluation: Ejecuta suite estadistica completa entre dos modelos.
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.adapters import EvaluatableModel, TfidfEvaluator
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


def load_predictions(csv_path: str) -> list[str]:
    """Carga la columna de predicciones desde un archivo CSV."""
    df = pd.read_csv(csv_path)
    col = "PREDICTION" if "PREDICTION" in df.columns else df.columns[-1]
    return df[col].astype(str).tolist()


def run_f1_evaluation(
    data_path: str,
    pred_path: str | None = None,
    model_name: str | None = None,
    enforce_gate: bool = True,
) -> float:
    """Evalua el Macro F1 de un modelo y valida el Quality Gate de CI/CD."""
    y_true = load_ground_truth(data_path)

    if pred_path:
        y_pred = load_predictions(pred_path)
        if len(y_pred) < len(y_true):
            print(
                f"⚠️ Muestra parcial: evaluando {len(y_pred)} de {len(y_true)} casos."
            )
            y_true = y_true[: len(y_pred)]
    elif model_name == "tfidf":
        evaluator: EvaluatableModel = TfidfEvaluator()
        df = pd.read_csv(data_path)
        y_pred = evaluator.predict_batch(df["DESCRIPTION"].tolist())
    else:
        raise ValueError("Debes especificar --model tfidf o --pred <archivo.csv>")

    score = evaluate_predictions(y_true, y_pred)["macro_f1"]
    print(f"--- [EVALUACION F1] Dataset: {data_path} ---")
    print(f"Macro F1-Score: {score:.4f}")

    if enforce_gate:
        check_quality_gate(score, min_f1=MIN_MACRO_F1)
        print("✅ APROBADO: Cumple con el Quality Gate de produccion.")
    return score


def run_mcnemar_evaluation(
    data_path: str, pred_a_path: str, pred_b_path: str
) -> dict[str, float]:
    """Compara estadisticamente las discordancias entre dos modelos via McNemar."""
    y_true = load_ground_truth(data_path)
    y_pred_a = load_predictions(pred_a_path)
    y_pred_b = load_predictions(pred_b_path)

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
    return mc


def run_bootstrap_evaluation(
    data_path: str, pred_a_path: str, pred_b_path: str
) -> dict[str, float]:
    """Calcula intervalo de confianza al 95% para la diferencia de Macro F1 (B - A)."""
    y_true = load_ground_truth(data_path)
    y_pred_a = load_predictions(pred_a_path)
    y_pred_b = load_predictions(pred_b_path)

    boot = paired_bootstrap_macro_f1(y_true, y_pred_a, y_pred_b)
    print(f"\n[Bootstrap Pareado (Macro F1, 1000 iteraciones)]")
    print(f"  Delta promedio (B - A): {boot['mean_delta']:+.4f}")
    print(
        f"  IC 95%:                [{boot['ci_lower']:+.4f}, {boot['ci_upper']:+.4f}]"
    )
    print(f"  p-value empirico:       {boot['p_value']:.6f}")
    return boot


def run_comparative_evaluation(
    data_path: str, pred_a_path: str, pred_b_path: str
) -> None:
    """Ejecuta el analisis estadistico comparativo completo (F1s + McNemar + Bootstrap)."""
    y_true = load_ground_truth(data_path)
    y_pred_a = load_predictions(pred_a_path)
    y_pred_b = load_predictions(pred_b_path)

    f1_a = evaluate_predictions(y_true, y_pred_a)["macro_f1"]
    f1_b = evaluate_predictions(y_true, y_pred_b)["macro_f1"]

    print(f"--- [COMPARACION DE MODELOS] ---")
    print(f"Modelo A ({pred_a_path}): Macro F1 = {f1_a:.4f}")
    print(f"Modelo B ({pred_b_path}): Macro F1 = {f1_b:.4f}")

    run_mcnemar_evaluation(data_path, pred_a_path, pred_b_path)
    run_bootstrap_evaluation(data_path, pred_a_path, pred_b_path)


DISPATCHER = {
    "f1": lambda args: run_f1_evaluation(
        data_path=args.data,
        pred_path=args.pred,
        model_name=args.model,
        enforce_gate=not args.no_gate,
    ),
    "mcnemar": lambda args: run_mcnemar_evaluation(
        data_path=args.data,
        pred_a_path=args.pred_a,
        pred_b_path=args.pred_b,
    ),
    "bootstrap": lambda args: run_bootstrap_evaluation(
        data_path=args.data,
        pred_a_path=args.pred_a,
        pred_b_path=args.pred_b,
    ),
    "all": lambda args: run_comparative_evaluation(
        data_path=args.data,
        pred_a_path=args.pred_a,
        pred_b_path=args.pred_b,
    ),
}


def build_parser() -> argparse.ArgumentParser:
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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    action = DISPATCHER.get(args.metric)
    if not action:
        parser.error(f"Metrica no soportada: {args.metric}")
    action(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ RECHAZADO: {err}", file=sys.stderr)
        sys.exit(1)

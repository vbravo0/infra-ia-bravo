"""Modulo de Evaluacion de Metricas y Significancia Estadistica (MLOps / LLMOps).

Sigue el principio de Responsabilidad Unica (SRP):
- Subcomandos CLI dedicados (f1, mcnemar, bootstrap, all) sin parametros huerfanos.
- Funciones de computo desacopladas de I/O y de formateo de texto.
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.metrics import (
    MIN_MACRO_F1,
    check_quality_gate,
    evaluate_predictions,
    mcnemar_test,
    paired_bootstrap_macro_f1,
)

# ---------------------------------------------------------------------------
# 1. Carga y alineacion de datos (I/O)
# ---------------------------------------------------------------------------


def load_series(csv_path: str, column_name: str) -> list[str]:
    """Lee una columna especifica de un CSV eliminando registros nulos."""
    df = pd.read_csv(csv_path)
    if column_name in df.columns:
        col = df[column_name]
    else:
        col = df.iloc[:, -1]
    return col.dropna().astype(str).tolist()


def align_predictions(
    y_true: list[str], y_pred: list[str]
) -> tuple[list[str], list[str]]:
    """Alinea el tamano de las listas cortando a la menor longitud comun."""
    min_len = min(len(y_true), len(y_pred))
    return y_true[:min_len], y_pred[:min_len]


# ---------------------------------------------------------------------------
# 2. Casos de Uso / Comandos de Evaluacion (Logica de Negocio)
# ---------------------------------------------------------------------------


def evaluate_f1(data_path: str, pred_path: str, enforce_gate: bool) -> float:
    """Calcula Macro F1 y valida contra el umbral minimo de produccion."""
    raw_true = load_series(data_path, "SEVERITY")
    raw_pred = load_series(pred_path, "PREDICTION")
    y_true, y_pred = align_predictions(raw_true, raw_pred)

    score = evaluate_predictions(y_true, y_pred)["macro_f1"]
    print(f"--- [EVALUACION F1] Dataset: {data_path} | Predicciones: {pred_path} ---")
    print(f"Muestras evaluadas: {len(y_true)}")
    print(f"Macro F1-Score:     {score:.4f}")

    if enforce_gate:
        check_quality_gate(score, min_f1=MIN_MACRO_F1)
        print("✅ APROBADO: Cumple con el Quality Gate de produccion.")
    return score


def evaluate_mcnemar(
    data_path: str, pred_a_path: str, pred_b_path: str
) -> dict[str, float]:
    """Calcula el test de significancia de McNemar entre dos modelos."""
    y_true = load_series(data_path, "SEVERITY")
    y_pred_a = load_series(pred_a_path, "PREDICTION")
    y_pred_b = load_series(pred_b_path, "PREDICTION")

    min_len = min(len(y_true), len(y_pred_a), len(y_pred_b))
    res = mcnemar_test(y_true[:min_len], y_pred_a[:min_len], y_pred_b[:min_len])

    print(f"\n[Test de McNemar] (Muestras: {min_len})")
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


def evaluate_bootstrap(
    data_path: str, pred_a_path: str, pred_b_path: str
) -> dict[str, float]:
    """Calcula el intervalo de confianza al 95% para la diferencia de Macro F1 (B - A)."""
    y_true = load_series(data_path, "SEVERITY")
    y_pred_a = load_series(pred_a_path, "PREDICTION")
    y_pred_b = load_series(pred_b_path, "PREDICTION")

    min_len = min(len(y_true), len(y_pred_a), len(y_pred_b))
    res = paired_bootstrap_macro_f1(
        y_true[:min_len], y_pred_a[:min_len], y_pred_b[:min_len]
    )

    print(f"\n[Bootstrap Pareado (Macro F1, 1000 iteraciones)] (Muestras: {min_len})")
    print(f"  Delta promedio (B - A): {res['mean_delta']:+.4f}")
    print(f"  IC 95%:                [{res['ci_lower']:+.4f}, {res['ci_upper']:+.4f}]")
    print(f"  p-value empirico:       {res['p_value']:.6f}")
    return res


def evaluate_all(data_path: str, pred_a_path: str, pred_b_path: str) -> None:
    """Ejecuta la suite comparativa completa: F1 individuales + McNemar + Bootstrap."""
    y_true = load_series(data_path, "SEVERITY")
    y_pred_a = load_series(pred_a_path, "PREDICTION")
    y_pred_b = load_series(pred_b_path, "PREDICTION")

    min_len = min(len(y_true), len(y_pred_a), len(y_pred_b))
    f1_a = evaluate_predictions(y_true[:min_len], y_pred_a[:min_len])["macro_f1"]
    f1_b = evaluate_predictions(y_true[:min_len], y_pred_b[:min_len])["macro_f1"]

    print("--- [COMPARACION DE MODELOS] ---")
    print(f"Modelo A ({pred_a_path}): Macro F1 = {f1_a:.4f}")
    print(f"Modelo B ({pred_b_path}): Macro F1 = {f1_b:.4f}")

    evaluate_mcnemar(data_path, pred_a_path, pred_b_path)
    evaluate_bootstrap(data_path, pred_a_path, pred_b_path)


# ---------------------------------------------------------------------------
# 3. Interfaz de Linea de Comandos (CLI via Subparsers estrictos)
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluador de metricas y significancia estadistica"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando: f1
    p_f1 = subparsers.add_parser("f1", help="Evalua Macro F1 y valida Quality Gate")
    p_f1.add_argument(
        "--data", default="data/sample_1000.csv", help="Dataset con ground truth"
    )
    p_f1.add_argument("--pred", required=True, help="CSV con predicciones del modelo")
    p_f1.add_argument("--no-gate", action="store_true", help="No abortar si F1 < 0.60")

    # Helper para subcomandos comparativos (pred-a y pred-b obligatorios)
    def add_comparison_args(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--data", default="data/sample_1000.csv", help="Dataset con ground truth"
        )
        subparser.add_argument(
            "--pred-a", required=True, help="CSV predicciones Modelo A"
        )
        subparser.add_argument(
            "--pred-b", required=True, help="CSV predicciones Modelo B"
        )

    p_mcnemar = subparsers.add_parser("mcnemar", help="Calcula test de McNemar")
    add_comparison_args(p_mcnemar)

    p_bootstrap = subparsers.add_parser("bootstrap", help="Calcula Bootstrap pareado")
    add_comparison_args(p_bootstrap)

    p_all = subparsers.add_parser(
        "all", help="Ejecuta comparacion completa (F1s + McNemar + Bootstrap)"
    )
    add_comparison_args(p_all)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "f1": lambda: evaluate_f1(args.data, args.pred, not args.no_gate),
        "mcnemar": lambda: evaluate_mcnemar(args.data, args.pred_a, args.pred_b),
        "bootstrap": lambda: evaluate_bootstrap(args.data, args.pred_a, args.pred_b),
        "all": lambda: evaluate_all(args.data, args.pred_a, args.pred_b),
    }

    handler = commands.get(args.command)
    if not handler:
        parser.error(f"Comando desconocido: {args.command}")
    handler()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ RECHAZADO: {err}", file=sys.stderr)
        sys.exit(1)

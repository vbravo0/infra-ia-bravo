"""Metricas de evaluacion y tests de significancia estadistica (REQ-08, REQ-09).

Implementa:
- Macro F1-Score y Quality Gate
- Test de McNemar con correccion de continuidad de Edwards
- Bootstrap pareado para estimacion de diferencia de Macro F1 con IC 95%
"""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2
from sklearn.metrics import f1_score

MIN_MACRO_F1 = 0.60


def evaluate_predictions(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    """Calcula el Macro F1 real sobre las etiquetas observadas y predichas."""
    score = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return {"macro_f1": score}


def check_quality_gate(macro_f1: float, min_f1: float = MIN_MACRO_F1) -> None:
    """Valida si el Macro F1 cumple con el umbral minimo aceptable para produccion.

    Si no lo cumple, lanza ValueError para abortar el pipeline de CI/CD.
    """
    if macro_f1 < min_f1:
        raise ValueError(
            f"Quality gate rechazado: Macro F1={macro_f1:.4f} inferior al umbral minimo ({min_f1:.4f})"
        )


def mcnemar_test(
    y_true: list[str] | np.ndarray,
    y_pred_a: list[str] | np.ndarray,
    y_pred_b: list[str] | np.ndarray,
) -> dict[str, float]:
    """Test de McNemar con correccion de continuidad de Edwards (REQ-09).

    Compara dos modelos sobre el mismo dataset:
    - b: A acierta y B falla
    - c: A falla y B acierta
    Estadistico: chi2 = (|b - c| - 1)^2 / (b + c)
    """
    y_t = np.array(y_true)
    correct_a = np.array(y_pred_a) == y_t
    correct_b = np.array(y_pred_b) == y_t

    b = int(np.sum(correct_a & ~correct_b))
    c = int(np.sum(~correct_a & correct_b))

    total_discordant = b + c
    if total_discordant == 0:
        return {"b": 0, "c": 0, "statistic": 0.0, "p_value": 1.0}

    statistic = float((abs(b - c) - 1.0) ** 2 / total_discordant)
    p_value = float(1.0 - chi2.cdf(statistic, df=1))

    return {"b": b, "c": c, "statistic": statistic, "p_value": p_value}


def paired_bootstrap_macro_f1(
    y_true: list[str] | np.ndarray,
    y_pred_a: list[str] | np.ndarray,
    y_pred_b: list[str] | np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap pareado sobre Macro F1 entre dos modelos (REQ-09).

    Estima el intervalo de confianza (IC 95%) de la diferencia:
    delta = F1(modelo_b) - F1(modelo_a)
    """
    rng = np.random.RandomState(seed)
    y_t = np.array(y_true)
    y_a = np.array(y_pred_a)
    y_b = np.array(y_pred_b)
    n = len(y_t)

    deltas = []
    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, size=n)
        f1_a = f1_score(y_t[idx], y_a[idx], average="macro", zero_division=0)
        f1_b = f1_score(y_t[idx], y_b[idx], average="macro", zero_division=0)
        deltas.append(f1_b - f1_a)

    deltas = np.array(deltas)
    return {
        "mean_delta": float(np.mean(deltas)),
        "ci_lower": float(np.percentile(deltas, 2.5)),
        "ci_upper": float(np.percentile(deltas, 97.5)),
        "p_value": float(np.mean(deltas <= 0)),
    }

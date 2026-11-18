"""Tests unitarios de significancia estadistica para comparacion de modelos (REQ-09).

Implementa y valida el Test de McNemar (aciertos) y Bootstrap pareado (Macro F1)
acordados en la devolucion del foro con el docente David Petrocelli.
"""

import numpy as np
from evaluate import mcnemar_test, paired_bootstrap_macro_f1


def test_mcnemar_identical_models_yields_p_value_one():
    """Verifica que dos modelos con identicas predicciones den estadistico 0 y p=1."""
    y_true = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] * 10
    y_pred_a = list(y_true)
    y_pred_b = list(y_true)

    res = mcnemar_test(y_true, y_pred_a, y_pred_b)

    assert res["b"] == 0
    assert res["c"] == 0
    assert res["statistic"] == 0.0
    assert res["p_value"] == 1.0


def test_mcnemar_detects_significant_difference():
    """Verifica que un modelo notablemente superior produzca un p-valor significativo (< 0.05)."""
    # y_true con 100 casos
    y_true = ["CRITICAL"] * 100
    # Modelo A acierta solo 40
    y_pred_a = ["CRITICAL"] * 40 + ["MEDIUM"] * 60
    # Modelo B acierta 85 (mejora contundente)
    y_pred_b = ["CRITICAL"] * 85 + ["MEDIUM"] * 15

    res = mcnemar_test(y_true, y_pred_a, y_pred_b)

    # b: A acierta y B falla (~0), c: A falla y B acierta (~45)
    assert res["c"] > res["b"]
    assert res["statistic"] > 3.84  # valor critico chi2 a 95%
    assert res["p_value"] < 0.01


def test_paired_bootstrap_identical_models_yields_zero_delta():
    """Verifica que dos modelos identicos tengan un delta promedio centrado en cero."""
    y_true = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] * 25
    y_pred = list(y_true)

    res = paired_bootstrap_macro_f1(y_true, y_pred, y_pred, n_bootstraps=100)

    assert abs(res["mean_delta"]) < 1e-6
    assert abs(res["ci_lower"]) < 1e-6
    assert abs(res["ci_upper"]) < 1e-6


def test_paired_bootstrap_superior_model_has_positive_ci():
    """Verifica que un modelo significativamente mejor tenga intervalo de confianza positivo."""
    np.random.seed(42)
    y_true = np.array(["LOW", "MEDIUM", "HIGH", "CRITICAL"] * 50)
    # Modelo A (bajo rendimiento, muchas fallas)
    y_pred_a = np.array(["MEDIUM"] * len(y_true))
    # Modelo B (acierta la gran mayoria)
    y_pred_b = np.copy(y_true)

    res = paired_bootstrap_macro_f1(
        y_true, y_pred_a, y_pred_b, n_bootstraps=200, seed=42
    )

    # La diferencia B - A debe ser claramente positiva
    assert res["mean_delta"] > 0.40
    assert res["ci_lower"] > 0.30
    assert res["p_value"] < 0.01

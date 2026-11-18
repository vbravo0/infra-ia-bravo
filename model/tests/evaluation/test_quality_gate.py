"""Tests unitarios del Quality Gate de Macro F1 (REQ-08).

Separa estrictamente la evaluacion del modelo de los tests de software/API.
"""

import pytest  # type: ignore
from eval.evaluate_tfidf import check_quality_gate, evaluate_predictions


def test_quality_gate_passes_when_macro_f1_meets_threshold():
    """No lanza excepcion cuando Macro F1 cumple el umbral minimo (0.60)."""
    check_quality_gate(macro_f1=0.65, min_f1=0.60)


def test_quality_gate_raises_error_when_macro_f1_drops():
    """Frena el deploy con ValueError cuando Macro F1 cae por debajo del minimo."""
    with pytest.raises(ValueError, match="Quality gate rechazado"):
        check_quality_gate(macro_f1=0.55, min_f1=0.60)


def test_evaluate_predictions_computes_correct_macro_f1():
    """Verifica que evaluate_predictions retorne el diccionario de metricas esperado."""
    y_true = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    y_pred = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    metrics = evaluate_predictions(y_true, y_pred)

    assert "macro_f1" in metrics
    assert metrics["macro_f1"] == 1.0

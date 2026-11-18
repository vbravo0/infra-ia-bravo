"""Modulo de Evaluacion de Calidad y Significancia Estadistica (MLOps / LLMOps).

Soporta evaluacion polimorfica via Protocol/Trait para:
- TF-IDF (clasificador en scikit-learn / joblib)
- LLM (Ollama con soporte para comparar prompts y generar checkpoints)

Uso CLI:
    python model/eval/evaluate.py --model tfidf
    python model/eval/evaluate.py --model llm --prompt model/prompts/system_prompt.txt
    python model/eval/evaluate.py --compare --prompt-a model/prompts/prompt_a.txt --prompt-b model/prompts/prompt_b.txt
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Protocol, Sequence
import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.metrics import f1_score

MIN_MACRO_F1 = 0.60


class EvaluatableModel(Protocol):
    """Protocol / Trait para cualquier modelo que prediga una lista de descripciones."""

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        """Recibe descripciones de CVEs y retorna la lista de etiquetas de severidad."""
        ...


class TfidfEvaluator:
    """Adaptador de evaluacion para el modelo scikit-learn (TF-IDF + LogisticRegression)."""

    def __init__(self, model_path: str = "model.joblib"):
        import joblib

        bundle = joblib.load(model_path)
        self.model = bundle["model"]

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        return list(self.model.predict(descriptions))


class OllamaEvaluator:
    """Adaptador de evaluacion para LLMs en Ollama con persistencia de checkpoints."""

    def __init__(
        self,
        prompt_path: str,
        checkpoint_path: str | None = None,
        model_name: str = "qwen2.5:1.5b",
        ollama_url: str = "http://localhost:11434/api/chat",
    ):
        with open(prompt_path, encoding="utf-8") as f:
            self.prompt_text = f.read().strip()
        self.checkpoint_path = checkpoint_path
        self.model_name = model_name
        self.ollama_url = ollama_url

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        """Corre inferencia sincrona/batch llamando a la API de Ollama con checkpointing."""
        import httpx
        from domain.predictor import OllamaPredictor

        options = {
            "temperature": 0.0,
            "seed": 42,
            "num_predict": 10,
            "num_gpu": 0,
        }
        predictor = OllamaPredictor(prompt_text=self.prompt_text, options=options)

        # Cargar checkpoint previo si existe para no re-ejecutar
        predictions: list[str] = []
        start_idx = 0
        if self.checkpoint_path and os.path.exists(self.checkpoint_path):
            df_ckpt = pd.read_csv(self.checkpoint_path)
            predictions = df_ckpt["PREDICTION"].tolist()
            start_idx = len(predictions)
            print(
                f"Retomando desde checkpoint: {start_idx}/{len(descriptions)} casos listos."
            )

        async def _run() -> list[str]:
            for i in range(start_idx, len(descriptions)):
                desc = descriptions[i]
                severity, _, _, _ = await predictor.predict(desc)
                predictions.append(severity)
                if (i + 1) % 25 == 0 or (i + 1) == len(descriptions):
                    print(f"Progreso LLM: {i + 1}/{len(descriptions)}...")
                    if self.checkpoint_path:
                        pd.DataFrame({"PREDICTION": predictions}).to_csv(
                            self.checkpoint_path, index=False
                        )
            return predictions

        return asyncio.run(_run())


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
    """Test de McNemar con correccion de continuidad de Edwards (REQ-09)."""
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
    """Bootstrap pareado sobre Macro F1 entre dos modelos (REQ-09)."""
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


def run_evaluation(
    evaluator: EvaluatableModel,
    data_path: str = "data/sample_1000.csv",
    enforce_gate: bool = True,
) -> float:
    """Evalua un modelo generico que cumpla el Protocol EvaluatableModel."""
    print(f"--- Evaluando modelo sobre {data_path} ---")
    df = pd.read_csv(data_path).dropna(subset=["DESCRIPTION", "SEVERITY"])

    y_true = df["SEVERITY"].tolist()
    y_pred = evaluator.predict_batch(df["DESCRIPTION"].tolist())

    metrics = evaluate_predictions(y_true, y_pred)
    macro_f1 = metrics["macro_f1"]
    print(f"Resultado: Macro F1-Score = {macro_f1:.4f}")

    if enforce_gate:
        check_quality_gate(macro_f1, min_f1=MIN_MACRO_F1)
        print("✅ APROBADO: Cumple con el Quality Gate de produccion.")
    return macro_f1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluador unificado de modelos CVE")
    parser.add_argument(
        "--model",
        choices=["tfidf", "llm"],
        default="tfidf",
        help="Tipo de modelo a evaluar (default: tfidf)",
    )
    parser.add_argument(
        "--data",
        default="data/sample_1000.csv",
        help="Ruta al dataset de evaluacion",
    )
    parser.add_argument(
        "--model-path",
        default="model.joblib",
        help="Ruta al binario joblib (para tfidf)",
    )
    parser.add_argument(
        "--prompt",
        default="model/prompts/system_prompt.txt",
        help="Ruta al system prompt (para llm)",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Ruta a CSV de checkpoint para inferencias largas de LLM",
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="No lanzar error si Macro F1 < 0.60 (util para diagnostico)",
    )

    args = parser.parse_args()

    if args.model == "tfidf":
        evaluator: EvaluatableModel = TfidfEvaluator(model_path=args.model_path)
    else:
        evaluator = OllamaEvaluator(
            prompt_path=args.prompt,
            checkpoint_path=args.checkpoint,
        )

    run_evaluation(
        evaluator=evaluator,
        data_path=args.data,
        enforce_gate=not args.no_gate,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"❌ RECHAZADO: {err}", file=sys.stderr)
        sys.exit(1)

"""Adaptadores de inferencia (EvaluatableModel Protocol) para TF-IDF y Ollama."""

from __future__ import annotations

import asyncio
import os
from typing import Protocol, Sequence
import pandas as pd


class EvaluatableModel(Protocol):
    """Protocol / Trait para cualquier modelo que prediga una lista de descripciones."""

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        """Recibe descripciones de CVEs y retorna la lista de etiquetas de severidad."""
        ...


class TfidfEvaluator:
    """Adaptador de inferencia para el modelo supervisado TF-IDF + LogisticRegression."""

    def __init__(self, model_path: str = "model.joblib"):
        import joblib

        bundle = joblib.load(model_path)
        self.model = bundle["model"]

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        return list(self.model.predict(descriptions))


class OllamaEvaluator:
    """Adaptador de inferencia para LLMs en Ollama con persistencia de checkpoints."""

    def __init__(
        self,
        prompt_path: str,
        checkpoint_path: str | None = None,
        model_name: str = "qwen2.5:1.5b",
        ollama_url: str | None = None,
    ):
        with open(prompt_path, encoding="utf-8") as f:
            self.prompt_text = f.read().strip()
        self.checkpoint_path = checkpoint_path
        self.model_name = model_name or os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.ollama_url = ollama_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434/api/chat"
        )

    def _load_checkpoint(self, total_expected: int) -> list[str]:
        """Carga predicciones previas si el archivo de checkpoint existe."""
        if not self.checkpoint_path or not os.path.exists(self.checkpoint_path):
            return []

        df_ckpt = pd.read_csv(self.checkpoint_path)
        predictions = df_ckpt["PREDICTION"].dropna().tolist()
        print(
            f"Retomando desde checkpoint: {len(predictions)}/{total_expected} casos listos."
        )
        return predictions

    def _save_checkpoint(self, predictions: list[str]) -> None:
        """Persiste las predicciones acumuladas a disco."""
        if self.checkpoint_path:
            pd.DataFrame({"PREDICTION": predictions}).to_csv(
                self.checkpoint_path, index=False
            )

    async def _predict_stream(
        self,
        descriptions: Sequence[str],
        initial_predictions: list[str],
    ) -> list[str]:
        """Ejecuta inferencia elemento a elemento guardando checkpoints cada 25 casos."""
        from domain.predictor import OllamaPredictor

        options = {
            "temperature": 0.0,
            "seed": 42,
            "num_predict": 10,
            "num_gpu": 0,
        }
        predictor = OllamaPredictor(prompt_text=self.prompt_text, options=options)
        predictions = list(initial_predictions)
        total = len(descriptions)

        for i in range(len(predictions), total):
            severity, _, _, _ = await predictor.predict(descriptions[i])
            predictions.append(severity)

            if (i + 1) % 25 == 0 or (i + 1) == total:
                print(f"Progreso LLM: {i + 1}/{total}...")
                self._save_checkpoint(predictions)

        return predictions

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        """Punto de entrada sincrono que orquesta checkpointing e inferencia."""
        cached_predictions = self._load_checkpoint(len(descriptions))
        if len(cached_predictions) >= len(descriptions):
            return cached_predictions[: len(descriptions)]

        return asyncio.run(self._predict_stream(descriptions, cached_predictions))

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
        ollama_url: str | None = None,
    ):
        with open(prompt_path, encoding="utf-8") as f:
            self.prompt_text = f.read().strip()
        self.checkpoint_path = checkpoint_path
        self.model_name = model_name or os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.ollama_url = ollama_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434/api/chat"
        )

    def predict_batch(self, descriptions: Sequence[str]) -> list[str]:
        """Corre inferencia asincrona llamando a la API de Ollama con checkpointing."""
        from domain.predictor import OllamaPredictor

        options = {
            "temperature": 0.0,
            "seed": 42,
            "num_predict": 10,
            "num_gpu": 0,
        }
        predictor = OllamaPredictor(prompt_text=self.prompt_text, options=options)

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

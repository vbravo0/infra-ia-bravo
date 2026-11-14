"""Definicion del Trait de inferencia (Protocol) e implementaciones desacopladas."""

from typing import Optional, Protocol
from adapters.ml_classifier import is_ready, predict_tfidf
from adapters.ollama_client import predict_llm


class SeverityPredictor(Protocol):
    """Trait/Protocol para cualquier motor de prediccion de severidad."""

    async def predict(self, description: str) -> tuple[str, Optional[float], bool, str]:
        """Ejecuta inferencia sobre la descripcion de un CVE.

        Args:
            description: Texto explicativo de la vulnerabilidad.

        Returns:
            Tupla (severity, confidence, parse_error, raw_output).
        """
        ...


class TfidfPredictor:
    """Implementacion del trait usando clasificador supervisado en memoria (scikit-learn)."""

    async def predict(self, description: str) -> tuple[str, Optional[float], bool, str]:
        severity, conf = predict_tfidf(description)
        return severity, conf, False, ""


class OllamaPredictor:
    """Implementacion del trait consumiendo el LLM via API REST estructurada."""

    def __init__(
        self,
        prompt_text: str,
        options: Optional[dict[str, Any]] = None,
    ):
        self.prompt_text = prompt_text
        self.options = options

    async def predict(self, description: str) -> tuple[str, Optional[float], bool, str]:
        return await predict_llm(self.prompt_text, description, options=self.options)


class FakePredictor:
    """Implementacion controlada para tests unitarios y de integracion."""

    def __init__(
        self,
        severity: str = "LOW",
        confidence: Optional[float] = 0.95,
        parse_error: bool = False,
        raw_output: str = "fake",
    ):
        self.severity = severity
        self.confidence = confidence
        self.parse_error = parse_error
        self.raw_output = raw_output
        self.calls: list[str] = []

    async def predict(self, description: str) -> tuple[str, Optional[float], bool, str]:
        self.calls.append(description)
        return self.severity, self.confidence, self.parse_error, self.raw_output

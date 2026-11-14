"""Trait de persistencia (Protocol) e implementaciones de repositorio."""

from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from domain.schemas import PredictResult


class CveRepository(Protocol):
    """Trait/Protocol para persistencia de clasificaciones y feedback de CVEs."""

    def save_prediction(self, res: PredictResult, description: str) -> None:
        """Persiste una inferencia en la historia."""
        ...

    def list_history(self, limit: int = 15) -> list[dict[str, Any]]:
        """Consulta los ultimos registros de inferencia."""
        ...

    def get_predictions_for_cve(self, cve_id: str) -> list[dict[str, Any]]:
        """Retorna las ultimas predicciones por motor para un cve_id."""
        ...

    def append_feedback(
        self,
        cve_id: str,
        actual_severity: str,
        source: str = "human",
        notes: Optional[str] = None,
    ) -> int:
        """Registra un evento inmutable de feedback y retorna su ID."""
        ...


class FakeCveRepository:
    """Implementacion simulada en memoria basada en listas exclusivamente para tests."""

    def __init__(self):
        self.history: list[dict[str, Any]] = []
        self.feedbacks: list[dict[str, Any]] = []
        self._history_id_seq = 0
        self._feedback_id_seq = 0

    def save_prediction(self, res: PredictResult, description: str) -> None:
        self._history_id_seq += 1
        record = {
            "id": self._history_id_seq,
            "cve_id": res.cve_id,
            "engine": res.engine,
            "severity": res.severity,
            "confidence": res.confidence,
            "parse_error": 1 if res.parse_error else 0,
            "model_version": res.model_version,
            "prompt_hash": res.prompt_hash,
            "latency_ms": res.latency_ms,
            "description": description,
            "raw_llm": res.raw_llm,
            "created_at": datetime.now(timezone.utc),
        }
        self.history.append(record)

    def list_history(self, limit: int = 15) -> list[dict[str, Any]]:
        # Ultimos registros en orden cronologico inverso
        return list(reversed(self.history))[:limit]

    def get_predictions_for_cve(self, cve_id: str) -> list[dict[str, Any]]:
        # Ultima prediccion de cada motor para ese cve_id (DISTINCT ON engine)
        latest_by_engine: dict[str, dict[str, Any]] = {}
        for rec in self.history:
            if rec["cve_id"] == cve_id:
                latest_by_engine[rec["engine"]] = rec
        return list(latest_by_engine.values())

    def append_feedback(
        self,
        cve_id: str,
        actual_severity: str,
        source: str = "human",
        notes: Optional[str] = None,
    ) -> int:
        self._feedback_id_seq += 1
        record = {
            "id": self._feedback_id_seq,
            "cve_id": cve_id,
            "actual_severity": actual_severity,
            "source": source,
            "notes": notes,
            "created_at": datetime.now(timezone.utc),
        }
        self.feedbacks.append(record)
        return self._feedback_id_seq

"""Adaptador de persistencia usando PostgreSQL nativo."""

from typing import Any, Optional
import psycopg  # type: ignore
from psycopg.rows import dict_row  # type: ignore
from config import DATABASE_URL
from domain.schemas import PredictResult


class PostgresCveRepository:
    """Implementacion del trait CveRepository conectandose a PostgreSQL."""

    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url

    def _get_connection(self):
        return psycopg.connect(self.db_url)

    def save_prediction(self, res: PredictResult, description: str) -> None:
        """Persiste el resultado de una clasificacion en la tabla history."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO history (
                        cve_id, engine, severity, confidence, parse_error,
                        model_version, prompt_hash, latency_ms, description, raw_llm
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        res.cve_id,
                        res.engine,
                        res.severity,
                        res.confidence,
                        1 if res.parse_error else 0,
                        res.model_version,
                        res.prompt_hash,
                        res.latency_ms,
                        description,
                        res.raw_llm,
                    ),
                )

    def list_history(self, limit: int = 15) -> list[dict[str, Any]]:
        """Consulta los ultimos registros clasificados en orden cronologico inverso."""
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM history ORDER BY id DESC LIMIT %s", (limit,))
                return cur.fetchall()

    def get_predictions_for_cve(self, cve_id: str) -> list[dict[str, Any]]:
        """Obtiene la ultima prediccion por motor emitida para un cve_id."""
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (engine) id, cve_id, engine, severity, created_at
                    FROM history
                    WHERE cve_id = %s
                    ORDER BY engine, id DESC
                    """,
                    (cve_id,),
                )
                return cur.fetchall()

    def append_feedback(
        self,
        cve_id: str,
        actual_severity: str,
        source: str = "human",
        notes: Optional[str] = None,
    ) -> int:
        """Registra un evento de feedback append-only con timestamp."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback_events (cve_id, actual_severity, source, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (cve_id, actual_severity, source, notes),
                )
                row = cur.fetchone()
                return row[0] if row else 0

    def list_feedbacks(self, limit: int = 15) -> list[dict[str, Any]]:
        """Consulta los ultimos eventos de feedback en orden cronologico inverso."""
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM feedback_events ORDER BY id DESC LIMIT %s", (limit,)
                )
                return cur.fetchall()

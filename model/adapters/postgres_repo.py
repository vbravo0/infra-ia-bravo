from typing import Any
import psycopg
from psycopg.rows import dict_row
from config import DATABASE_URL
from domain.schemas import PredictResult


def get_connection():
    return psycopg.connect(DATABASE_URL)


def save_prediction(res: PredictResult, description: str) -> None:
    with get_connection() as conn:
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


def list_history(limit: int = 15) -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM history ORDER BY id DESC LIMIT %s", (limit,))
            return cur.fetchall()


def update_feedback(cve_id: str, actual_severity: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE history
                SET actual_severity = %s
                WHERE cve_id = %s
                """,
                (actual_severity, cve_id),
            )
            return cur.rowcount

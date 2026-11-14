from typing import Any
import psycopg
from psycopg.rows import dict_row
from config import DATABASE_URL
from domain.schemas import PredictResult


def get_connection():
    """Abre y retorna una conexion activa a la base de datos PostgreSQL."""
    return psycopg.connect(DATABASE_URL)


def save_prediction(res: PredictResult, description: str) -> None:
    """Persiste el resultado de una clasificacion en la tabla history.

    Args:
        res: PredictResult con metadatos de la prediccion.
        description: Texto crudo del CVE evaluado.
    """
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
    """Consulta los ultimos registros clasificados en orden cronologico inverso.

    Args:
        limit: Maximo de filas a retornar (default 15).

    Returns:
        Lista de diccionarios con el historial de predicciones.
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM history ORDER BY id DESC LIMIT %s", (limit,))
            return cur.fetchall()


def update_feedback(cve_id: str, actual_severity: str) -> list[dict[str, Any]]:
    """Registra la severidad real o correccion humana para un cve_id existente.

    Args:
        cve_id: Identificador del CVE a conciliar.
        actual_severity: Etiqueta confirmada (LOW, MEDIUM, HIGH, CRITICAL).

    Returns:
        Lista de filas actualizadas con prediccion original y nueva severidad.
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE history
                SET actual_severity = %s
                WHERE cve_id = %s
                RETURNING id, cve_id, engine, severity, actual_severity
                """,
                (actual_severity, cve_id),
            )
            return cur.fetchall()

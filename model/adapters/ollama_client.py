from typing import Optional
import httpx
from config import OLLAMA_MODEL, OLLAMA_URL, VALID_CLASSES


def _build_prompt(system_prompt: str, description: str) -> str:
    return (
        f"{system_prompt}\n\n"
        f"Descripcion del CVE: {description}\n\n"
        f"Responde EXACTAMENTE una sola palabra en mayusculas (LOW, MEDIUM, HIGH o CRITICAL):\n"
    )


def _parse_output(raw: str) -> tuple[str, Optional[float], bool]:
    # Validación estricta: si la respuesta no es exactamente una de las 4 clases, falla como UNKNOWN.
    # Para LLM la confianza es None (no inventa probabilidades).
    token = raw.strip().upper()
    if token in VALID_CLASSES:
        return token, None, False
    return "UNKNOWN", None, True


async def predict_llm(
    system_prompt: str, description: str
) -> tuple[str, Optional[float], bool, str]:
    full_prompt = _build_prompt(system_prompt, description)
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 25,
                    },
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip().upper()
    except Exception as exc:
        raw = f"OLLAMA_ERR: {exc}"

    severity, conf, parse_error = _parse_output(raw)
    return severity, conf, parse_error, raw

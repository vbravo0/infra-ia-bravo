import json
from typing import Optional
import httpx
from config import OLLAMA_MODEL, OLLAMA_URL, VALID_CLASSES


def _build_messages(system_prompt: str, description: str) -> list[dict[str, str]]:
    """Construye los mensajes para la API /api/chat encapsulando la entrada en JSON.

    Args:
        system_prompt: Instrucciones base del modelo y analista.
        description: Texto libre de la vulnerabilidad a clasificar.

    Returns:
        Lista de diccionarios con roles 'system' y 'user'.
    """
    user_payload = json.dumps({"description": description}, ensure_ascii=False)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_payload},
    ]


def _parse_output(raw: str) -> tuple[str, Optional[float], bool]:
    """Valida que la salida del LLM pertenezca estrictamente a las 4 clases CVSS.

    Args:
        raw: Texto crudo devuelto por el modelo.

    Returns:
        Tupla (severidad, confianza, parse_error). Para LLM la confianza es None.
    """
    token = raw.strip().upper()
    if token in VALID_CLASSES:
        return token, None, False
    return "UNKNOWN", None, True


async def predict_llm(
    system_prompt: str, description: str
) -> tuple[str, Optional[float], bool, str]:
    """Ejecuta inferencia asincrona contra el LLM en Ollama.

    Args:
        system_prompt: Prompt del sistema cargado desde disco.
        description: Descripcion del CVE.

    Returns:
        Tupla (severidad, confianza, parse_error, raw_text).
    """
    messages = _build_messages(system_prompt, description)
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": 0.0,
                        "seed": 42,
                        "top_k": 1,
                        "num_predict": 10,
                        "num_gpu": 0,  # Fuerza inferencia exclusivamente en CPU para determinismo estricto
                    },
                },
            )
            resp.raise_for_status()
            message_obj = resp.json().get("message", {})
            raw = message_obj.get("content", "").strip().upper()
    except Exception as exc:
        raw = f"OLLAMA_ERR: {exc}"

    severity, conf, parse_error = _parse_output(raw)
    return severity, conf, parse_error, raw

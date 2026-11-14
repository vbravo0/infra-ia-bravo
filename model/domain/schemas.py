from typing import Optional
from pydantic import BaseModel


class PredictRequest(BaseModel):
    cve_id: str = "CVE-2024-39300"
    description: str
    engine: str = "tfidf"


class PredictResult(BaseModel):
    cve_id: str
    engine: str
    severity: str
    model_hash: str
    confidence: Optional[float] = None
    model_version: str
    prompt_hash: str
    latency_ms: float
    parse_error: bool = False
    raw_llm: str = ""

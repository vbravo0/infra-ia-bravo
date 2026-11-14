import os
from pathlib import Path

PORT = int(os.environ.get("PORT", "8081"))
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")

BASE_DIR = Path(__file__).parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", BASE_DIR / "model.joblib"))
PROMPT_PATH = Path(
    os.environ.get("PROMPT_PATH", BASE_DIR / "prompts" / "system_prompt.txt")
)
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://cve_user:cve_pass@postgres:5432/cve_db"
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.k3d.internal:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
VALID_CLASSES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

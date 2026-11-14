import hashlib
from config import PROMPT_PATH


def load_prompt() -> tuple[str, str]:
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    short_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return text, short_hash

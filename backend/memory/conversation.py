import json
from pathlib import Path

from backend.config import CONVERSATION_DIR, MAX_HISTORY_MESSAGES


def _path(session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_") or "default"
    return CONVERSATION_DIR / f"{safe}.json"


def load_history(session_id: str) -> list[dict]:
    path = _path(session_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_history(session_id: str, history: list[dict]) -> None:
    _path(session_id).write_text(
        json.dumps(history[-MAX_HISTORY_MESSAGES:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_history(session_id: str) -> None:
    path = _path(session_id)
    if path.exists():
        path.unlink()

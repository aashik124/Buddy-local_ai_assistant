from pathlib import Path

from backend.config import DOCUMENT_DIR


def list_documents() -> list[str]:
    return [path.name for path in DOCUMENT_DIR.iterdir() if path.is_file()]


def read_document(name: str) -> str:
    path = (DOCUMENT_DIR / name).resolve()
    if DOCUMENT_DIR.resolve() not in path.parents:
        raise ValueError("Invalid document path")
    return path.read_text(encoding="utf-8", errors="ignore")[:12000]

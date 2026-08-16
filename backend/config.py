from pathlib import Path

import os

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

MEMORY_DIR = DATA_DIR / "memory"

for directory in [DATA_DIR, MEMORY_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

CONVERSATION_DIR = DATA_DIR / "conversations"
DOCUMENT_DIR = DATA_DIR / "documents"

OLLAMA_CHAT_URL = "http://127.0.0.1:11434/v1/chat/completions"
DEFAULT_MODEL = "qwen3:8b"
MAX_HISTORY_MESSAGES = 24
QDRANT_URL = "http://127.0.0.1:6333"
VECTOR_SIZE = 384
MEMORY_COLLECTION = "buddy_memory"
DOCUMENT_COLLECTION = "buddy_documents"



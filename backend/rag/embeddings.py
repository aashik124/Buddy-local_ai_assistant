import hashlib
import math
import re

from backend.config import VECTOR_SIZE


TOKEN_RE = re.compile(r"[a-zA-Z0-9_']+")


def embed_text(text: str) -> list[float]:
    """Small local embedding fallback.

    This uses hashed bag-of-words vectors so Qdrant works immediately without a
    model download. Swap this file for Sentence Transformers when you want
    stronger semantic retrieval.
    """
    vector = [0.0] * VECTOR_SIZE
    for token in TOKEN_RE.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(text) for text in texts]

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.config import MEMORY_COLLECTION, QDRANT_URL, VECTOR_SIZE
from backend.rag.embeddings import embed_text


def client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_memory_collection() -> None:
    qdrant = client()
    collections = {item.name for item in qdrant.get_collections().collections}
    if MEMORY_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=MEMORY_COLLECTION,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )


def save_memory(text: str, kind: str = "fact") -> None:
    ensure_memory_collection()
    client().upsert(
        collection_name=MEMORY_COLLECTION,
        points=[
            models.PointStruct(
                id=str(uuid4()),
                vector=embed_text(text),
                payload={"text": text, "kind": kind},
            )
        ],
    )


def search_memory(query: str, limit: int = 5) -> list[str]:
    try:
        ensure_memory_collection()
        hits = client().search(
            collection_name=MEMORY_COLLECTION,
            query_vector=embed_text(query),
            limit=limit,
            with_payload=True,
        )
        return [str(hit.payload.get("text", "")) for hit in hits if hit.payload and hit.payload.get("text")]
    except Exception:
        return []

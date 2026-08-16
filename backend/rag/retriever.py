from pathlib import Path
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.config import DOCUMENT_COLLECTION, DOCUMENT_DIR, QDRANT_URL, VECTOR_SIZE
from backend.rag.chunker import chunk_text
from backend.rag.embeddings import embed_text, embed_texts
from backend.rag.loader import SUPPORTED_EXTENSIONS, load_text


def client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_document_collection() -> None:
    qdrant = client()
    collections = {item.name for item in qdrant.get_collections().collections}
    if DOCUMENT_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=DOCUMENT_COLLECTION,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )


def ingest_document(path: Path) -> int:
    ensure_document_collection()
    text = load_text(path)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    points = [
        models.PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload={"text": chunk, "source": path.name},
        )
        for chunk, vector in zip(chunks, embed_texts(chunks))
    ]
    client().upsert(collection_name=DOCUMENT_COLLECTION, points=points)
    return len(points)


def ingest_documents() -> dict[str, int]:
    counts = {}
    for path in DOCUMENT_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                counts[path.name] = ingest_document(path)
            except Exception as exc:
                counts[path.name] = f"error: {exc}"
    return counts


def retrieve(query: str, limit: int = 4) -> list[str]:
    try:
        ensure_document_collection()
        hits = client().search(
            collection_name=DOCUMENT_COLLECTION,
            query_vector=embed_text(query),
            limit=limit,
            with_payload=True,
        )
        results = []
        for hit in hits:
            if not hit.payload or not hit.payload.get("text"):
                continue
            source = hit.payload.get("source", "document")
            results.append(f"{source}: {hit.payload['text']}")
        return results
    except Exception:
        return []

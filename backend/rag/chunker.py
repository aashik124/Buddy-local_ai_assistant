def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
        if start <= 0:
            start = end
    return [chunk.strip() for chunk in chunks if chunk.strip()]

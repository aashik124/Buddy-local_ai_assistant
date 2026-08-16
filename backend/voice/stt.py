"""Local speech-to-text using faster-whisper.

The whisper model is loaded once (lazily, on first use) and reused for every
request. Model size can be changed via WHISPER_MODEL_SIZE below - "small" is
a good balance of speed/accuracy on CPU; use "base" or "tiny" for faster but
less accurate results, or "medium"/"large-v3" if you have a GPU.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"          # change to "cuda" if you have an NVIDIA GPU + CUDA installed
WHISPER_COMPUTE_TYPE = "int8"   # "int8" is fastest on CPU; use "float16" on GPU

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _model


def _transcribe_sync(path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(path, beam_size=5, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe_audio(path: str) -> str:
    """Transcribes an audio file (wav/mp3/webm/ogg/m4a - anything ffmpeg can read) to text."""
    if not Path(path).exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    return await asyncio.to_thread(_transcribe_sync, path)

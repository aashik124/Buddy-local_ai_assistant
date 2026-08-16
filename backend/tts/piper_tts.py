"""Local text-to-speech using Piper, with a full character voice roster.

Piper itself only ships "real" trained voices (whichever .onnx files you
download), and it has exactly two delivery knobs that matter for character:
  - length_scale   : speed (lower = faster)
  - noise_scale / noise_w_scale : expressiveness / natural variation

Piper does NOT have a pitch knob. To get genuinely different-sounding
characters (a squeaky cartoon voice, a deep monster voice, a flat robot
voice) out of only two downloaded base models, this file layers a second,
cheap-but-effective trick on top: after Piper renders the WAV, we relabel
the WAV's sample rate in its header (without touching the audio samples).
Playing audio "faster than it was recorded" raises its pitch and speed
together (the classic chipmunk/record-sped-up effect); playing it slower
lowers pitch and speed together (monster/deep effect). Combined with Piper's
own speed/expressiveness knobs, this is enough to produce a small cast of
distinct-sounding characters from just two source voices.

Add more real Piper voices any time by dropping additional .onnx (+
.onnx.json) files into data/voices/ and registering them in VOICE_FILES —
see https://github.com/rhasspy/piper/blob/master/VOICES.md for the full list.
"""
from __future__ import annotations

import io
import re
import wave

from piper import PiperVoice, SynthesisConfig

from backend.config import BASE_DIR

VOICE_DIR = BASE_DIR / "data" / "voices"

# ------------------------------------------------------------------
# BASE MODELS — the only files you actually need to download.
# ------------------------------------------------------------------
VOICE_FILES = {
    "neutral_male": VOICE_DIR / "en_US-lessac-medium.onnx",
    "soft_female": VOICE_DIR / "en_US-amy-medium.onnx",
}

_loaded_voices: dict[str, PiperVoice] = {}


def _get_voice(key: str) -> PiperVoice:
    if key not in _loaded_voices:
        if key not in VOICE_FILES:
            raise ValueError(f"Unknown base voice '{key}'. Options: {list(VOICE_FILES)}")
        path = VOICE_FILES[key]
        if not path.exists():
            raise FileNotFoundError(
                f"Voice model not found at {path}. Download it from "
                "https://github.com/rhasspy/piper/blob/master/VOICES.md and place it in data/voices/."
            )
        _loaded_voices[key] = PiperVoice.load(str(path))
    return _loaded_voices[key]


def available_base_voices() -> list[str]:
    return list(VOICE_FILES)


# ------------------------------------------------------------------
# CHARACTER VOICE ROSTER
# ------------------------------------------------------------------
# base           -> which downloaded Piper model to render with
# length_scale   -> speed (Piper). <1 faster, >1 slower
# noise_scale    -> expressiveness/variation (Piper)
# noise_w_scale  -> variation in phoneme timing (Piper)
# pitch_shift    -> our own playback-rate trick. <1 deeper, >1 higher/squeakier.
#                   1.0 = untouched, no post-processing applied.
VOICE_PRESETS = {
    "neutral_male": {
        "base": "neutral_male", "length_scale": 1.00, "noise_scale": 0.667,
        "noise_w_scale": 0.8, "pitch_shift": 1.00,
        "label": "Neutral Male",
    },
    "soft_female": {
        "base": "soft_female", "length_scale": 1.00, "noise_scale": 0.667,
        "noise_w_scale": 0.8, "pitch_shift": 1.00,
        "label": "Soft Female",
    },
    "deep_narrator": {
        "base": "neutral_male", "length_scale": 1.22, "noise_scale": 0.45,
        "noise_w_scale": 0.5, "pitch_shift": 0.80,
        "label": "Deep Narrator",
    },
    "cartoon": {
        "base": "soft_female", "length_scale": 0.80, "noise_scale": 0.95,
        "noise_w_scale": 1.05, "pitch_shift": 1.42,
        "label": "Cartoon / Chipmunk",
    },
    "hyper_squeaky": {
        "base": "soft_female", "length_scale": 0.66, "noise_scale": 1.05,
        "noise_w_scale": 1.1, "pitch_shift": 1.68,
        "label": "Hyper Squeaky",
    },
    "monster": {
        "base": "neutral_male", "length_scale": 1.40, "noise_scale": 0.4,
        "noise_w_scale": 0.45, "pitch_shift": 0.62,
        "label": "Monster / Giant",
    },
    "robot": {
        "base": "neutral_male", "length_scale": 0.98, "noise_scale": 0.12,
        "noise_w_scale": 0.15, "pitch_shift": 0.97,
        "label": "Robot",
    },
}

DEFAULT_VOICE = "cartoon"


def available_voice_presets() -> dict[str, str]:
    """Returns {preset_key: display_label} for building a frontend dropdown."""
    return {key: cfg["label"] for key, cfg in VOICE_PRESETS.items()}


# ------------------------------------------------------------------
# EMOTION -> DELIVERY MULTIPLIERS (layered on top of the chosen voice preset)
# ------------------------------------------------------------------
EMOTION_MULTIPLIERS = {
    "happy":    {"length_mult": 0.94, "noise_mult": 1.10},
    "excited":  {"length_mult": 0.87, "noise_mult": 1.20},
    "sad":      {"length_mult": 1.18, "noise_mult": 0.75},
    "thinking": {"length_mult": 1.10, "noise_mult": 0.88},
    "oops":     {"length_mult": 1.05, "noise_mult": 0.85},
    "neutral":  {"length_mult": 1.00, "noise_mult": 1.00},
}


def detect_emotion(text: str) -> str:
    lower = text.lower()
    if re.search(r"haha|hehe|lol|funny|joke|laugh|giggle", lower):
        return "happy"
    if re.search(r"wow|whoa|amazing|great|awesome|yes!", lower):
        return "excited"
    if re.search(r"sad|tired|stress|hurt|cry", lower):
        return "sad"
    if re.search(r"think|maybe|hmm|let me|checking", lower):
        return "thinking"
    if re.search(r"oops|error|sorry|uh oh|problem", lower):
        return "oops"
    return "neutral"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ------------------------------------------------------------------
# PITCH-SHIFT TRICK — relabel the WAV's sample rate, samples untouched.
# ------------------------------------------------------------------
def _shift_playback_rate(wav_bytes: bytes, multiplier: float) -> bytes:
    if multiplier == 1.0:
        return wav_bytes

    with wave.open(io.BytesIO(wav_bytes), "rb") as reader:
        params = reader.getparams()
        frames = reader.readframes(reader.getnframes())

    new_rate = max(4000, int(params.framerate * multiplier))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(params.nchannels)
        writer.setsampwidth(params.sampwidth)
        writer.setframerate(new_rate)
        writer.writeframes(frames)

    buffer.seek(0)
    return buffer.read()


# ------------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------------
def synthesize(text: str, emotion: str | None = None, voice: str | None = None) -> bytes:
    """Synthesizes speech for `text`.

    `voice` selects a character preset (see VOICE_PRESETS / available_voice_presets()).
    `emotion` nudges delivery for this message; if omitted it's auto-detected from the text.
    """
    preset = VOICE_PRESETS.get(voice or DEFAULT_VOICE, VOICE_PRESETS[DEFAULT_VOICE])
    emo = emotion or detect_emotion(text)
    mult = EMOTION_MULTIPLIERS.get(emo, EMOTION_MULTIPLIERS["neutral"])

    piper_voice = _get_voice(preset["base"])
    syn_config = SynthesisConfig(
        length_scale=_clamp(preset["length_scale"] * mult["length_mult"], 0.4, 2.2),
        noise_scale=_clamp(preset["noise_scale"] * mult["noise_mult"], 0.05, 1.4),
        noise_w_scale=preset["noise_w_scale"],
        normalize_audio=True,
    )

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        piper_voice.synthesize_wav(text, wav_file, syn_config=syn_config)
    buffer.seek(0)
    raw_wav = buffer.read()

    return _shift_playback_rate(raw_wav, preset["pitch_shift"])

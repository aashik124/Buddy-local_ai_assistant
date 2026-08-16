import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import BASE_DIR, DEFAULT_MODEL
from backend.llm.ollama import complete_chat
from backend.llm.prompts import system_prompt
from backend.memory.conversation import clear_history, load_history, save_history
from backend.memory.long_term import forget_profile, load_profile, remember_fact, save_profile
from backend.memory.vector_memory import save_memory, search_memory
from backend.rag.retriever import ingest_documents, retrieve
from backend.tools.system import get_time
from backend.tools.vision import describe_image
from backend.tools.weather import get_weather
from backend.tools.web import format_results_for_prompt, web_search
from backend.tts.piper_tts import available_voice_presets, synthesize as piper_synthesize
from backend.voice.stt import transcribe_audio

app = FastAPI(title="Buddy Local AI Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = DEFAULT_MODEL


class ClearRequest(BaseModel):
    session_id: str = "default"


class SpeakRequest(BaseModel):
    text: str
    emotion: str | None = None
    voice: str | None = None


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "model": DEFAULT_MODEL}


@app.get("/api/voices")
def voices():
    """Lists selectable TTS voice presets, for populating the frontend dropdown."""
    return {"voices": available_voice_presets()}


@app.post("/api/clear")
def clear_chat(request: ClearRequest):
    clear_history(request.session_id)
    return {"ok": True}


@app.post("/api/forget")
def forget():
    forget_profile()
    return {"ok": True}


@app.post("/api/speak")
def speak(request: SpeakRequest):
    text = request.text.strip()
    if not text:
        return Response(status_code=400)
    try:
        audio_bytes = piper_synthesize(text, emotion=request.emotion, voice=request.voice)
    except (FileNotFoundError, ValueError) as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})
    return Response(content=audio_bytes, media_type="audio/wav")


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Accepts a recorded audio clip (webm/wav/mp3/etc.) and returns its transcript
    using the local faster-whisper model — a real backend speech-to-text path,
    independent of the browser's built-in Web Speech API."""
    suffix = Path(audio.filename or "clip.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        text = await transcribe_audio(tmp_path)
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"text": text}


@app.post("/api/vision")
async def vision(image: UploadFile = File(...), question: str = Form("Describe this image in detail.")):
    """Accepts an uploaded image and a question, and returns a description/answer
    using a local multimodal Ollama model (see backend/tools/vision.py)."""
    image_bytes = await image.read()
    mime_type = image.content_type or "image/jpeg"
    try:
        answer = await describe_image(image_bytes, question=question, mime_type=mime_type)
    except Exception as exc:
        return JSONResponse(status_code=503, content={
            "error": f"Vision model unavailable: {exc}. Run `ollama pull llava` and try again."
        })
    return {"answer": answer}


@app.post("/api/ingest-documents")
def ingest_docs():
    return {"ok": True, "documents": ingest_documents()}


def update_profile_from_text(text: str) -> None:
    profile = load_profile()
    name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z .'-]{1,40})", text)
    if name_match:
        name = re.sub(r"[.!?].*", "", name_match.group(1)).strip()
        profile["name"] = name
        save_profile(profile)
        save_memory(f"User name is {name}", kind="profile")

    remember_match = re.search(r"\bremember(?: that)?\s+(.+)", text, re.I)
    if remember_match:
        fact = remember_match.group(1).strip()
        remember_fact(fact)
        save_memory(fact, kind="fact")


async def local_tool_answer(message: str) -> str | None:
    lower = message.lower()
    if re.search(r"\b(time|date)\b", lower):
        return f"Tada! Banana clock says {get_time('Asia/Kathmandu')}."

    weather_match = re.search(r"\bweather(?: in| at| for)?\s+([a-zA-Z .'-]{2,50})", message)
    if weather_match:
        return await get_weather(weather_match.group(1).strip())

    if "what is my name" in lower or "who am i" in lower:
        profile = load_profile()
        return (
            f"Hello! Your name is {profile['name']}. I kept it in my tiny memory pocket."
            if profile.get("name")
            else "Oopsie, I do not know your name yet. Tell me, and I will keep it in banana memory."
        )

    return None


WEB_SEARCH_TRIGGER = re.compile(r"\b(search|look up|google|find (?:info|information)) (?:for |about )?(.+)", re.I)


async def maybe_web_context(message: str) -> str | None:
    """If the message looks like a search request, runs a real web search and
    returns formatted context to append to the LLM prompt (RAG-style, but for
    live web results instead of local documents)."""
    match = WEB_SEARCH_TRIGGER.search(message)
    if not match:
        return None
    query = match.group(2).strip()
    if not query:
        return None
    results = await web_search(query)
    return format_results_for_prompt(results)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def event_stream():
        message = request.message.strip()
        if not message:
            return

        update_profile_from_text(message)
        history = load_history(request.session_id)
        profile = load_profile()
        memories = search_memory(message)
        document_chunks = retrieve(message)
        web_context = await maybe_web_context(message)

        tool_answer = await local_tool_answer(message)
        if tool_answer:
            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": tool_answer},
            ])
            save_history(request.session_id, history)
            yield tool_answer
            return

        extra_context = [*memories, *document_chunks]
        if web_context:
            extra_context.append(f"Live web search results:\n{web_context}")

        messages = [
            {"role": "system", "content": system_prompt(profile, extra_context)},
            *history[-18:],
            {"role": "user", "content": message},
        ]

        full = ""
        try:
            answer = await complete_chat(messages, model=request.model or DEFAULT_MODEL)
            full = answer or "I reached the model, but it returned an empty response."
        except Exception as exc:
            full = (
                "My local AI backend could not reach Ollama. "
                "Start Ollama and run `ollama pull qwen3:8b`, then try again. "
                f"Details: {exc}"
            )

        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": full},
        ])
        save_history(request.session_id, history)
        yield full

    return StreamingResponse(event_stream(), media_type="text/plain")

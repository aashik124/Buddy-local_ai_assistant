# Buddy — Local AI Assistant

Buddy is a locally hosted, ChatGPT-style AI assistant built with Python and FastAPI. It combines a local language model with voice interaction, memory, RAG, image understanding, web search, and other tools.

The project is designed to explore how different AI components can be integrated into a single personal assistant while keeping the core AI processing on the local machine.

## Features

* Conversational AI powered by **Ollama and Qwen3:8B**
* Image understanding using **LLaVA** or other Ollama vision models
* Speech-to-text using **faster-whisper**
* Text-to-speech using **Piper TTS**
* Seven configurable voice presets
* Conversation history and long-term memory
* Vector memory and document-based RAG using **Qdrant**
* Support for TXT, Markdown, Python, JavaScript, HTML, CSS, CSV, JSON, PDF, and DOCX files
* Live web search using DuckDuckGo
* Weather and time tools
* File and Python execution tools
* Browser-based and local backend speech recognition

## Architecture

```text
User
 │
 ▼
Frontend
 │
 ▼
FastAPI Backend
 │
 ├── Ollama ────────── Qwen3:8B
 │
 ├── Ollama ────────── Vision Model
 │
 ├── faster-whisper ── Speech-to-Text
 │
 ├── Piper ─────────── Text-to-Speech
 │
 ├── Qdrant ────────── Memory + RAG
 │
 └── Tools ─────────── Web / Weather / Files / Python
```

## Tech Stack

* **Backend:** Python, FastAPI
* **LLM:** Ollama, Qwen3:8B
* **Vision:** LLaVA
* **Speech Recognition:** faster-whisper
* **Text-to-Speech:** Piper
* **Vector Database:** Qdrant
* **Frontend:** HTML, CSS, JavaScript
* **Containerization:** Docker

## Getting Started

### Requirements

Make sure the following are installed:

* Python
* Ollama
* Docker
* Git

### Install the models

```powershell
ollama pull qwen3:8b
ollama pull llava
```

### Install dependencies

```powershell
cd local-ai-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Start Qdrant

```powershell
docker compose up -d qdrant
```

### Add Piper voices

Create the following directory:

```text
data/voices/
```

Add the required Piper voice files:

```text
en_US-lessac-medium.onnx
en_US-lessac-medium.onnx.json
en_US-amy-medium.onnx
en_US-amy-medium.onnx.json
```

These two base voices are used to generate the seven available voice presets.

### Run the application

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## RAG and Memory

Buddy uses Qdrant for both document retrieval and semantic memory.

Documents can be placed in:

```text
data/documents/
```

Supported formats include:

```text
.txt  .md  .py  .js  .html  .css
.csv  .json  .pdf  .docx
```

Documents can then be indexed through the backend and retrieved when they are relevant to a user's question.

The current embedding implementation uses a lightweight hashed bag-of-words approach. A future version can replace this with a trained embedding model such as `sentence-transformers` for better semantic retrieval.

## Voice

Buddy supports two speech-input methods:

1. Browser Web Speech API
2. Local speech recognition using `faster-whisper`

For speech output, Piper TTS is used with two base voice models to create seven different presets, including Neutral, Female, Narrator, Cartoon, Squeaky, Monster, and Robot styles.

## Vision and Web Search

Images can be uploaded and analyzed using a locally running Ollama vision model such as LLaVA.

Buddy can also perform live web searches using DuckDuckGo and provide the retrieved information to the language model as additional context.

## Local Architecture

Buddy is currently a **local-first application**. The backend and AI models run on the same computer:

```text
FastAPI
   ↓
Ollama
   ↓
Qwen3:8B
```

The Whisper, Piper, and Qdrant services also run locally.

Because these services depend on the local computer, the laptop must remain powered on and the required services must be running for Buddy to work. If the laptop is turned off, the backend and AI models are no longer available.

## Online Deployment

The project includes a Vercel entrypoint at:

```text
api/index.py
```

and Vercel config at:

```text
vercel.json
```

This can deploy the FastAPI shell, static frontend, and lightweight endpoints.
However, the **full local AI stack is not automatically available on Vercel**.

The local version depends on:

* Ollama running at `127.0.0.1:11434`
* Qdrant running at `127.0.0.1:6333`
* Piper `.onnx` voice files in `data/voices/`
* faster-whisper model downloads/cache

On Vercel, `127.0.0.1` means the Vercel function itself, not your laptop.
So the deployed app will need hosted replacements:

* Hosted LLM API instead of local Ollama, or a reachable cloud Ollama server
* Hosted Qdrant or another vector database
* Cloud TTS/STT, or a container/function setup large enough for local models
* External file/object storage for persistent data

A possible future architecture is:

```text
User
 ↓
Vercel Frontend
 ↓
Vercel / Cloud Backend
 ↓
Hosted LLM / STT / TTS / Vector DB
```

So: **yes, it is possible to launch a version on Vercel**, but the current
full-featured local version is best run on your PC or on a VPS/GPU server.
For production Vercel, convert the local dependencies to hosted services first.

## Project Structure

```text
local-ai-assistant/
├── frontend/
├── backend/
│   ├── llm/
│   ├── memory/
│   ├── rag/
│   ├── tools/
│   ├── voice/
│   └── tts/
├── data/
│   ├── documents/
│   ├── voices/
│   ├── memory/
│   ├── conversations/
│   └── qdrant/
├── requirements.txt
└── README.md
```

## Future Improvements

* Improved semantic embeddings and RAG
* Streaming responses
* Better real-time voice interaction
* Wake-word detection
* Improved tool calling
* Authentication and multi-user support
* Local and cloud model selection
* Cloud deployment
* Production security and API management

## Author

**Aashik Poudel**

IT Engineer (Bachelor of Engineering in Information Technology)

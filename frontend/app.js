const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const modelInput = document.getElementById("modelInput");
const listenBtn = document.getElementById("listenBtn");
const recordBtn = document.getElementById("recordBtn");
const newChatBtn = document.getElementById("newChatBtn");
const forgetBtn = document.getElementById("forgetBtn");
const voiceToggle = document.getElementById("voiceToggle");
const voiceStyle = document.getElementById("voiceStyle");
const testVoiceBtn = document.getElementById("testVoiceBtn");
const imageInput = document.getElementById("imageInput");
const askImageBtn = document.getElementById("askImageBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const avatar = document.querySelector(".avatar");

const sessionId = localStorage.getItem("buddy:session") || crypto.randomUUID();
localStorage.setItem("buddy:session", sessionId);

function setStatus(text, mode = "ready") {
  statusText.textContent = text;
  statusDot.className = mode === "busy" ? "busy" : mode === "error" ? "error" : "";
}

function addMessage(text, role) {
  const node = document.createElement("div");
  node.className = `msg ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function cleanForSpeech(text) {
  return text
    .replace(/\[[^\]]+\]/g, "")
    .replace(/\((?:laughing|laughs|giggles|sighs|gasps|thinking|smiles|cries)[^)]*\)/gi, "")
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "")
    .replace(/\b(?:laughing|crying|smiling|thinking|sad|happy)?\s*emoji\b/gi, "")
    .replace(/\bface with tears of joy\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

/*
  ============================================================
  REAL VOICE PRESETS — loaded from the backend (backend/tts/piper_tts.py)
  ============================================================
  The old version of this file faked different "characters" using the
  browser's built-in speechSynthesis pitch/rate knobs. Now that /api/speak
  renders real audio with Piper (including a genuine pitch-shift trick for
  cartoon/monster/robot voices — see piper_tts.py), the dropdown below is
  populated directly from GET /api/voices and the selected key is sent
  straight to the backend on every /api/speak call.
*/
async function loadVoiceOptions() {
  try {
    const response = await fetch("/api/voices");
    const data = await response.json();
    voiceStyle.innerHTML = "";
    for (const [key, label] of Object.entries(data.voices || {})) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = label;
      voiceStyle.appendChild(option);
    }
  } catch (error) {
    console.error("Could not load voice list:", error);
  }
}
loadVoiceOptions();

function reactionFor(text) {
  const lower = text.toLowerCase();
  if (/(haha|hehe|lol|funny|joke|laugh|giggle|teehee|banana)/.test(lower)) return "\u{1F602}";
  if (/(wow|whoa|amazing|tada|great|nice|awesome|yes!)/.test(lower)) return "\u2728";
  if (/(oops|error|sorry|uh oh|problem)/.test(lower)) return "\u{1F62C}";
  if (/(sad|tired|stress|hurt|cry)/.test(lower)) return "\u{1F97A}";
  if (/(think|maybe|hmm|let me|checking)/.test(lower)) return "\u{1F914}";
  return "\u{1F34C}";
}

function showReaction(text) {
  const emoji = reactionFor(text);
  const bubble = document.createElement("div");
  bubble.className = "reaction-pop";
  bubble.textContent = emoji;
  avatar.appendChild(bubble);
  avatar.dataset.mood = emoji;
  window.setTimeout(() => bubble.remove(), 1400);
}

let audioContext;
function getAudioContext() {
  if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
  return audioContext;
}

function chirpSequence(frequencies, duration = 0.075, type = "triangle", gainValue = 0.045) {
  try {
    const ctx = getAudioContext();
    let time = ctx.currentTime;
    frequencies.forEach(frequency => {
      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.type = type;
      oscillator.frequency.setValueAtTime(frequency, time);
      gain.gain.setValueAtTime(0.0001, time);
      gain.gain.exponentialRampToValueAtTime(gainValue, time + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
      oscillator.connect(gain).connect(ctx.destination);
      oscillator.start(time);
      oscillator.stop(time + duration + 0.02);
      time += duration * 0.72;
    });
  } catch (error) {
    // Optional expression sounds may be blocked until the user interacts.
  }
}

function playExpressionSound(text) {
  const reaction = reactionFor(text);
  if (reaction === "\u{1F602}") chirpSequence([820, 1120, 960, 1280, 1040], 0.055, "square", 0.035);
  else if (reaction === "\u2728") chirpSequence([720, 960, 1320], 0.07, "triangle", 0.04);
  else if (reaction === "\u{1F62C}") chirpSequence([340, 260], 0.12, "sawtooth", 0.035);
  else if (reaction === "\u{1F914}") chirpSequence([420, 520, 460], 0.09, "sine", 0.025);
}

function playIntroSound() {
  chirpSequence([760, 980, 1250, 1180, 1420], 0.055, "square", 0.032);
}

/*
  ============================================================
  REAL NEURAL VOICE (Piper, via backend)
  ============================================================
  Sends text + the selected voice preset key to /api/speak, which runs
  actual Piper synthesis (see backend/tts/piper_tts.py) and returns a WAV
  file. Emotion is auto-detected server-side from the text.
*/
let currentAudio = null;

async function speak(text) {
  if (!voiceToggle.checked) return;
  const spoken = cleanForSpeech(text);
  if (!spoken) return;

  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  try {
    const response = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: spoken, voice: voiceStyle.value || null }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    currentAudio = new Audio(audioUrl);
    currentAudio.onended = () => URL.revokeObjectURL(audioUrl);
    currentAudio.play();
  } catch (error) {
    console.error("Speech generation failed:", error);
    setStatus("Voice error", "error");
  }
}

async function sendMessage(text) {
  addMessage(text, "user");
  const assistant = addMessage("", "assistant");
  setStatus("Thinking", "busy");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        model: modelInput.value || "qwen3:8b",
      }),
    });

    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let full = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      full += chunk;
      assistant.textContent = full;
      messages.scrollTop = messages.scrollHeight;
    }

    setStatus("Ready");
    showReaction(full);
    playExpressionSound(full);
    speak(full);
  } catch (error) {
    assistant.textContent = `Backend error: ${error.message}`;
    setStatus("Error", "error");
  }
}

chatForm.addEventListener("submit", event => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  sendMessage(text);
});

newChatBtn.addEventListener("click", async () => {
  messages.innerHTML = "";
  await fetch("/api/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  addMessage("New chat started.", "system");
});

forgetBtn.addEventListener("click", async () => {
  await fetch("/api/forget", { method: "POST" });
  addMessage("Long-term memory cleared.", "system");
});

testVoiceBtn.addEventListener("click", () => {
  const sample = "Hello! This is a quick test of the selected voice. Banana mode ready!";
  showReaction(sample);
  playIntroSound();
  speak(sample);
});

/*
  ============================================================
  VOICE INPUT — TWO PATHS
  ============================================================
  1) Browser Web Speech API ("Start listening") — fast, no backend round
     trip, but relies on the browser/OS's own recognizer.
  2) Backend faster-whisper ("Record (backend STT)") — records real audio
     with MediaRecorder and POSTs it to /api/transcribe, which runs a local
     Whisper model server-side. Works offline and is the same engine
     regardless of browser.
*/
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.onstart = () => setStatus("Listening", "busy");
  recognition.onend = () => setStatus("Ready");
  recognition.onerror = () => setStatus("Voice error", "error");
  recognition.onresult = event => {
    const transcript = event.results[0][0].transcript;
    sendMessage(transcript);
  };
  listenBtn.addEventListener("click", () => recognition.start());
} else {
  listenBtn.disabled = true;
  listenBtn.textContent = "Browser STT unavailable";
}

let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

async function toggleBackendRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    setStatus("Recording unavailable", "error");
    return;
  }

  if (isRecording) {
    mediaRecorder.stop();
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = event => {
      if (event.data.size > 0) recordedChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      isRecording = false;
      recordBtn.textContent = "Record (backend STT)";
      stream.getTracks().forEach(track => track.stop());

      setStatus("Transcribing", "busy");
      const blob = new Blob(recordedChunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("audio", blob, "clip.webm");

      try {
        const response = await fetch("/api/transcribe", { method: "POST", body: formData });
        const data = await response.json();
        if (data.text) {
          sendMessage(data.text);
        } else {
          setStatus(data.error || "Transcription failed", "error");
        }
      } catch (error) {
        setStatus("Transcription failed", "error");
      }
    };

    mediaRecorder.start();
    isRecording = true;
    recordBtn.textContent = "Stop recording";
    setStatus("Recording", "busy");
  } catch (error) {
    setStatus("Microphone denied", "error");
  }
}

recordBtn.addEventListener("click", toggleBackendRecording);

/*
  ============================================================
  VISION — image upload + question, answered by a local multimodal
  Ollama model via /api/vision (see backend/tools/vision.py).
  ============================================================
*/
askImageBtn.addEventListener("click", async () => {
  const file = imageInput.files[0];
  if (!file) {
    setStatus("Choose an image first", "error");
    return;
  }

  const question = messageInput.value.trim() || "Describe this image in detail.";
  addMessage(`[image] ${question}`, "user");
  const assistant = addMessage("", "assistant");
  setStatus("Looking", "busy");

  const formData = new FormData();
  formData.append("image", file);
  formData.append("question", question);

  try {
    const response = await fetch("/api/vision", { method: "POST", body: formData });
    const data = await response.json();
    const answer = data.answer || data.error || "No response from the vision model.";
    assistant.textContent = answer;
    messageInput.value = "";
    setStatus("Ready");
    showReaction(answer);
    speak(answer);
  } catch (error) {
    assistant.textContent = `Vision error: ${error.message}`;
    setStatus("Error", "error");
  }
});

addMessage(
  "Buddy is ready. Start Ollama for the full local AI brain, or ask time/weather/name questions now. " +
  "Try 'search for ...' for live web results, upload an image for vision, or use either mic button for voice input.",
  "system"
);

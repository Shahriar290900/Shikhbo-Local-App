# CLAUDE.md — Shikhbo Local (local-first desktop app)

Read automatically by Claude Code. This is the desktop rebuild of Shikhbo: a
Bengali/English curriculum study assistant, packaged as `.dmg` (macOS) and
`.exe` (Windows). It must be bulletproof — it should never crash, and it should
recover from missing pieces on its own.

## The core rule: LOCAL-FIRST, not air-gapped
The app MAY use the internet for: downloading the Ollama models, downloading
STT/TTS voice models, and app updates. The app MUST NOT send user or curriculum
content anywhere. Specifically, these NEVER leave the machine:
- the user's prompts and the model's answers
- retrieved curriculum chunks / RAG context
- chat history
- the user's microphone audio
No cloud LLM, no cloud RAG, no cloud STT/TTS, no telemetry containing user
content. The ONLY allowed remote traffic is downloading models/voices/updates.
LLM inference and all data processing happen locally. If you find user content
going to a non-localhost host, that's a bug — fix it.

## Bulletproof principles (apply everywhere)
- Never crash on a missing dependency. Detect, explain, and recover (download,
  rebuild, fall back, or degrade gracefully — text chat must always work).
- Idempotent setup: running first-run setup twice is safe.
- Self-heal: if the FAISS index is missing/corrupt, rebuild it from raw_data; if
  the DB is missing, create it; if a voice model is absent, download or disable
  that feature without breaking chat.
- Every external touchpoint (Ollama, mic, downloads) is wrapped with a timeout,
  a retry, and a clear user-facing message — never a stack trace.
- Log to a local file in the app-data dir; surface a friendly status in the UI.
- Use a real app-data dir (platformdirs) for DB, index, logs, and downloaded
  models — never write inside the app bundle (read-only after install).

## Repos / folders
- This workspace = the `Shikhbo-Local-App` repo (push target:
  https://github.com/Shahriar290900/Shikhbo-Local-App).
- `./Shikhbo-reference/` = original cloud app, READ-ONLY reference. Learn its
  pipeline, retriever, RRF, templates, and streaming contract; do not ship its
  cloud code.
- `./raw_data/` = curriculum corpus (JSONL: English unit*.jsonl, ICT_C*.jsonl);
  bundle it into the app so the index can always be rebuilt offline.

## Stack
- LLM: Ollama, `qwen3.5:0.8b` via `http://127.0.0.1:11434`, streaming. Model id
  configurable via `OLLAMA_LLM_MODEL` (0.8b is small — RAG carries quality; a
  user with more RAM can set `qwen3.5:2b/4b/9b`).
- Embeddings: `bge-m3` via Ollama (`OLLAMA_EMBED_MODEL`), local. Best for Bengali.
- Retrieval: FAISS + BM25 + RRF (reuse reference logic).
- Backend: Flask, streaming NDJSON, started in a background thread on a free port.
- Shell: pywebview native window over the local Flask server.
- Frontend: reuse the reference repo's templates/static (minus login/cloud UI).
- Storage: SQLite in the app-data dir, chat history only, NO login.
- STT: local Whisper-based (e.g. faster-whisper / BanglaSpeech2Text) — Bengali.
- TTS: local Piper (check for a `bn` voice); fall back to eSpeak NG if none.
- Fonts: bundle Noto Sans Bengali locally via @font-face (no CDN) for correct
  conjunct (যুক্তাক্ষর) rendering on every OS, including bare Linux.

## Cloud → local swaps (what the reference does → what we do)
- Gemini API → Ollama `qwen3.5:0.8b`.
- HuggingFace embeddings API → Ollama `bge-m3` (the easy-to-miss offline breaker).
- NeonDB Postgres + OTP auth → local SQLite, no auth.
- Vercel → desktop app.
- **Browser Web Speech API (STT/TTS)** → local Whisper + Piper/eSpeak. The Web
  Speech API sends audio to Google AND isn't supported in macOS WKWebView, so it
  breaks in the desktop shell — treat it as a 5th cloud dependency to remove.

## Conventions
- Preserve the streaming states: thinking → retrieving → synthesizing → tokens
  → sources. The UX depends on it; add a `transcribing` state when STT runs.
- UTF-8 everywhere (read JSONL with encoding='utf-8'; SQLite/Flask UTF-8).
  Decode Ollama's per-token JSON text, not raw byte chunks (Bengali = 3-byte
  chars; naive splitting causes mojibake).
- Bengali is first-class; test retrieval + generation + STT on real raw_data.
- No API keys, no cloud env vars anywhere.

## Definition of done
Install the `.dmg`/`.exe` → first run sets up Ollama + models + voices with
progress → app opens straight into chat → ask a Bengali curriculum question →
thinking states → grounded streamed answer with sources → voice in (Bengali STT)
and out (TTS) work → history persists. With wifi off AFTER setup, chat still
works. Verified: no user/curriculum content ever sent to a remote host.

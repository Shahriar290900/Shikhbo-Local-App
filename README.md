# শিখবো — Shikhbo Local

A **local-first** Bengali/English curriculum AI tutor. Runs entirely on your device — no internet required after first setup.

## Privacy guarantee

Your questions, answers, and voice audio **never leave your machine**. The only remote traffic is downloading models/voices during setup. Chat works fully offline after setup.

## Requirements

- macOS 12+ or Windows 10+
- 4 GB RAM minimum (8 GB recommended for 2b+ models)
- ~3 GB disk for models

## Installation

### macOS
1. Download `Shikhbo-macOS.dmg` from [Releases](https://github.com/Shahriar290900/Shikhbo-Local-App/releases)
2. Open the `.dmg`, drag Shikhbo to Applications
3. Launch Shikhbo — the first-run wizard appears

### Windows
1. Download `Shikhbo-Windows-installer.exe` from [Releases](https://github.com/Shahriar290900/Shikhbo-Local-App/releases)
2. Run the installer
3. Launch Shikhbo from the Start menu or Desktop shortcut

## First run

The setup wizard will:
1. Check if [Ollama](https://ollama.com) is installed (if not, link to installer)
2. Download `qwen3.5:0.8b` (~600 MB, LLM) and `bge-m3` (~1 GB, embeddings)
3. Build the curriculum knowledge index from bundled JSONL files
4. Open straight into chat

Re-running setup is instant if already complete.

## Usage

1. Select a **Subject** (ICT, Bangla, Physics, English)
2. Select a **Mode** (Normal, Simple, Quiz, Step-by-Step)
3. Set your **Class** and **Curriculum** in the settings panel
4. Type your question and press Enter (or use the mic button for voice input)
5. The answer streams with status indicators: Thinking → Retrieving → Synthesizing → Answer

## Switching model size

For better answers (requires more RAM), edit the environment before launching:

```bash
# macOS / Linux
OLLAMA_LLM_MODEL=qwen3.5:2b python app.py

# Windows (PowerShell)
$env:OLLAMA_LLM_MODEL="qwen3.5:2b"; python app.py
```

Available sizes: `0.8b` (default, ~600 MB), `2b` (~1.5 GB), `4b` (~3 GB), `9b` (~6 GB)

## Running from source

```bash
# Install dependencies
pip install -r requirements.txt

# First run (setup wizard runs automatically if setup_complete.json is missing)
python app.py

# Or run setup manually
python app.py   # then open http://127.0.0.1:5050/setup
```

## Build installers locally

> PyInstaller cannot cross-compile: `.dmg` must be built on macOS, `.exe` on Windows.

```bash
pip install pyinstaller
pyinstaller shikhbo.spec --noconfirm

# macOS: create .dmg
hdiutil create -volname Shikhbo -srcfolder dist/Shikhbo.app -ov -format UDZO Shikhbo.dmg

# Windows: create installer (requires NSIS)
makensis /DOUTFILE="Shikhbo-installer.exe" /DAPP_DIR="dist\Shikhbo" installer.nsi
```

A tagged push to `main` triggers the GitHub Actions workflow that builds both installers automatically.

> **Note:** macOS Gatekeeper and Windows SmartScreen may warn about unsigned apps. To avoid this, you would need Apple notarization (macOS) or a code-signing certificate (Windows). See their respective documentation for details.

## Tech stack

| Component | Technology |
|---|---|
| LLM | Ollama `qwen3.5:0.8b` (local) |
| Embeddings | Ollama `bge-m3` (local) |
| Retrieval | FAISS + BM25 + RRF |
| Backend | Flask (Python) |
| Frontend | Vanilla JS / HTML / CSS |
| Database | SQLite (chat history only) |
| STT | faster-whisper (Bengali) |
| TTS | Piper (`bn` voice) → eSpeak NG fallback |
| Packaging | PyInstaller + GitHub Actions |

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, Response, redirect, render_template, request, jsonify, stream_with_context, url_for
from flask_cors import CORS
from platformdirs import user_data_dir
from werkzeug.utils import secure_filename

# ── App-data directory ────────────────────────────────────────────────────────
APP_NAME = "shikhbo"
APP_DATA = Path(user_data_dir(APP_NAME))
for sub in ("db", "index", "logs", "models"):
    (APP_DATA / sub).mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(APP_DATA / "logs" / "shikhbo.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"App-data dir: {APP_DATA}")

# ── Deferred imports (after sys.path is set) ──────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "shikhbo_local_secret_2025")
CORS(app)

UPLOAD_FOLDER = APP_DATA / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "pdf", "txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# ── Shared state ──────────────────────────────────────────────────────────────
_setup_complete = False
_setup_status: dict = {}
_ollama_proc = None
_pipeline_ready = False

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _free_port(start: int = 5050) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def _check_setup_complete() -> bool:
    flag = APP_DATA / "setup_complete.json"
    return flag.exists()


def _ensure_ollama() -> bool:
    """Ping Ollama; if binary exists but not serving, start it."""
    import requests as _requests
    global _ollama_proc

    try:
        r = _requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        pass

    # Try to start it
    ollama_bin = None
    for candidate in ["ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, timeout=3)
            ollama_bin = candidate
            break
        except Exception:
            continue

    if not ollama_bin:
        logger.warning("Ollama binary not found on PATH")
        return False

    try:
        _ollama_proc = subprocess.Popen(
            [ollama_bin, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Started ollama serve (pid={_ollama_proc.pid})")
        for _ in range(20):
            time.sleep(0.5)
            try:
                import requests as _r
                if _r.get("http://127.0.0.1:11434/api/tags", timeout=2).status_code == 200:
                    return True
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to start ollama: {e}")

    return False


def _load_pipeline():
    """Load retriever/pipeline; rebuild index if missing. Runs in background thread."""
    global _pipeline_ready
    try:
        from scripts.pipeline.retriever import Retriever
        from scripts.pipeline.pipeline import init_pipeline
        init_pipeline(APP_DATA / "index")
        _pipeline_ready = True
        logger.info("Pipeline ready")
    except Exception as e:
        logger.error(f"Pipeline load failed: {e}")
        _pipeline_ready = False


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if not _check_setup_complete():
        return redirect(url_for("setup_page"))
    return redirect(url_for("chat_page"))


@app.route("/chat")
def chat_page():
    from scripts.db.sqlite_db import get_recent_messages
    history = []
    try:
        history = get_recent_messages(limit=50)
    except Exception as e:
        logger.warning(f"Could not load history: {e}")
    return render_template("chat.html", history=history)


@app.route("/setup")
def setup_page():
    return render_template("setup.html")


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    import requests as _r
    ollama_ok = False
    try:
        ollama_ok = _r.get("http://127.0.0.1:11434/api/tags", timeout=2).status_code == 200
    except Exception:
        pass
    return jsonify({
        "ollama": ollama_ok,
        "pipeline": _pipeline_ready,
        "setup_complete": _check_setup_complete(),
    })


# ── Query (RAG streaming) ─────────────────────────────────────────────────────

@app.route("/api/query", methods=["POST"])
def query():
    file_path = None

    if request.content_type and "multipart/form-data" in request.content_type:
        try:
            messages = json.loads(request.form.get("messages", "[]"))
        except (json.JSONDecodeError, TypeError):
            messages = []

        subject = request.form.get("subject", "ICT")
        mode = request.form.get("mode", "normal")
        class_level = request.form.get("class_level", "SSC")
        curriculum = request.form.get("curriculum", "NCTB")
        latest_query = request.form.get("query", "").strip()

        if not messages and not latest_query:
            return jsonify({"error": "Query required."}), 400

        if not messages and latest_query:
            messages = [{"role": "user", "content": latest_query}]
        if not latest_query and messages:
            latest_query = messages[-1].get("content", "")

        uploaded_file = request.files.get("file")
        if uploaded_file and uploaded_file.filename:
            if not allowed_file(uploaded_file.filename):
                return jsonify({"error": "File type not allowed."}), 400
            filename = secure_filename(uploaded_file.filename)
            file_path = str(UPLOAD_FOLDER / filename)
            uploaded_file.save(file_path)
    else:
        data = request.get_json() or {}
        messages = data.get("messages", [])
        subject = data.get("subject", "ICT")
        mode = data.get("mode", "normal")
        class_level = data.get("class_level", "SSC")
        curriculum = data.get("curriculum", "NCTB")

        if not messages:
            latest_query = data.get("query", "").strip()
            if not latest_query:
                return jsonify({"error": "Query required."}), 400
            messages = [{"role": "user", "content": latest_query}]
        latest_query = messages[-1]["content"] if messages else ""

    user_json = {
        "query": latest_query,
        "class_level": class_level,
        "curriculum": curriculum,
        "subject": subject,
        "mode": mode,
        "messages": messages,
        "file_path": file_path,
    }

    def generate():
        full_reply = ""
        try:
            from scripts.pipeline.pipeline import run_pipeline_stream
            for payload in run_pipeline_stream(user_json):
                if "chunk" in payload:
                    full_reply += payload["chunk"]
                yield json.dumps(payload, ensure_ascii=False) + "\n"
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            yield json.dumps({"chunk": f"\n\nSomething went wrong: {e}"}) + "\n"
        finally:
            if file_path and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            if full_reply:
                try:
                    from scripts.db.sqlite_db import save_turn
                    save_turn(latest_query, full_reply)
                except Exception as e:
                    logger.warning(f"History save failed: {e}")

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


# ── Voice: STT ────────────────────────────────────────────────────────────────

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file."}), 400

    audio_file = request.files["audio"]
    audio_path = str(UPLOAD_FOLDER / "stt_input.wav")
    audio_file.save(audio_path)

    try:
        from scripts.voice.stt import transcribe_audio
        text = transcribe_audio(audio_path, model_dir=str(APP_DATA / "models" / "whisper"))
        return jsonify({"text": text})
    except Exception as e:
        logger.error(f"STT error: {e}")
        return jsonify({"error": str(e), "text": ""}), 500
    finally:
        if os.path.isfile(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ── Voice: TTS ────────────────────────────────────────────────────────────────

@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text."}), 400

    try:
        from scripts.voice.tts import synthesize
        wav_bytes = synthesize(text, model_dir=str(APP_DATA / "models" / "piper"))
        if wav_bytes:
            from flask import send_file
            import io
            return send_file(io.BytesIO(wav_bytes), mimetype="audio/wav")
        return jsonify({"tts_unavailable": True}), 200
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({"tts_unavailable": True, "error": str(e)}), 200


# ── Setup wizard steps ────────────────────────────────────────────────────────

@app.route("/api/setup/run", methods=["GET"])
def setup_run():
    def steps():
        import requests as _r

        yield json.dumps({"step": "ollama_check", "status": "running"}) + "\n"
        ollama_ok = _ensure_ollama()
        if not ollama_ok:
            yield json.dumps({"step": "ollama_check", "status": "error",
                              "message": "Ollama not found. Please install from https://ollama.com"}) + "\n"
            return
        yield json.dumps({"step": "ollama_check", "status": "done"}) + "\n"

        llm_model = os.getenv("OLLAMA_LLM_MODEL", "qwen3.5:0.8b")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

        for model in [llm_model, embed_model]:
            yield json.dumps({"step": "model_pull", "status": "running", "model": model}) + "\n"
            try:
                proc = subprocess.Popen(
                    ["ollama", "pull", model],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in proc.stdout:
                    yield json.dumps({"step": "model_pull", "status": "progress",
                                      "model": model, "line": line.strip()}) + "\n"
                proc.wait()
                if proc.returncode != 0:
                    yield json.dumps({"step": "model_pull", "status": "error", "model": model}) + "\n"
                    return
                yield json.dumps({"step": "model_pull", "status": "done", "model": model}) + "\n"
            except Exception as e:
                yield json.dumps({"step": "model_pull", "status": "error",
                                  "model": model, "message": str(e)}) + "\n"
                return

        yield json.dumps({"step": "build_index", "status": "running"}) + "\n"
        try:
            from build_index import build_index
            build_index(str(APP_DATA / "index"), str(PROJECT_ROOT / "raw_data"))
            yield json.dumps({"step": "build_index", "status": "done"}) + "\n"
        except Exception as e:
            yield json.dumps({"step": "build_index", "status": "error", "message": str(e)}) + "\n"
            return

        (APP_DATA / "setup_complete.json").write_text(
            json.dumps({"completed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}), encoding="utf-8"
        )

        threading.Thread(target=_load_pipeline, daemon=True).start()

        yield json.dumps({"step": "done", "status": "done"}) + "\n"

    return Response(stream_with_context(steps()), mimetype="application/x-ndjson")


# ── Entry point ───────────────────────────────────────────────────────────────

def _startup():
    """Run pre-flight checks in background after Flask starts."""
    # Initialize SQLite DB
    try:
        from scripts.db.sqlite_db import init_db
        init_db(APP_DATA / "db")
    except Exception as e:
        logger.error(f"DB init failed: {e}")

    _ensure_ollama()
    if _check_setup_complete():
        threading.Thread(target=_load_pipeline, daemon=True).start()


if __name__ == "__main__":
    threading.Thread(target=_startup, daemon=True).start()
    port = _free_port(5050)
    logger.info(f"Starting Shikhbo Local on http://127.0.0.1:{port}")
    app.run(debug=False, port=port, host="127.0.0.1", threaded=True, use_reloader=False)

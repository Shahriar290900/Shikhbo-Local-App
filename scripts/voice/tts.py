import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _try_piper(text: str, model_dir: str) -> bytes | None:
    """Synthesize with Piper using a Bengali voice if available."""
    piper_bin = shutil.which("piper") or shutil.which("piper-tts")
    if not piper_bin:
        return None

    model_dir_path = Path(model_dir)
    bn_voices = list(model_dir_path.glob("bn*.onnx"))
    if not bn_voices:
        logger.info("No Piper Bengali voice found in model_dir")
        return None

    voice_model = str(bn_voices[0])
    config = voice_model.replace(".onnx", ".json")
    if not Path(config).exists():
        logger.info("Piper voice config not found")
        return None

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        result = subprocess.run(
            [piper_bin, "--model", voice_model, "--config", config, "--output_file", wav_path],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and Path(wav_path).stat().st_size > 0:
            with open(wav_path, "rb") as f:
                return f.read()
    except subprocess.TimeoutExpired:
        logger.warning("Piper timed out")
    except Exception as e:
        logger.warning(f"Piper error: {e}")
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    return None


def _try_espeak(text: str) -> bytes | None:
    """Fallback: synthesize with eSpeak NG in Bengali."""
    espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak_bin:
        return None

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        result = subprocess.run(
            [espeak_bin, "-v", "bn", "-w", wav_path, text],
            capture_output=True,
            timeout=20,
        )
        if result.returncode == 0 and Path(wav_path).stat().st_size > 0:
            with open(wav_path, "rb") as f:
                return f.read()
    except subprocess.TimeoutExpired:
        logger.warning("eSpeak timed out")
    except Exception as e:
        logger.warning(f"eSpeak error: {e}")
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    return None


def synthesize(text: str, model_dir: str) -> bytes | None:
    """Return WAV bytes, or None if no TTS engine is available."""
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    result = _try_piper(text, model_dir)
    if result:
        logger.info("TTS via Piper")
        return result

    result = _try_espeak(text)
    if result:
        logger.info("TTS via eSpeak")
        return result

    logger.warning("No TTS engine available (Piper and eSpeak not found)")
    return None

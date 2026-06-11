import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_model_dir: str | None = None


def _load_model(model_dir: str):
    global _whisper_model, _whisper_model_dir
    if _whisper_model is not None and _whisper_model_dir == model_dir:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel
        model_size = "base"
        logger.info(f"Loading Whisper model '{model_size}' into {model_dir}")
        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            download_root=model_dir,
        )
        _whisper_model_dir = model_dir
        logger.info("Whisper model loaded")
        return _whisper_model
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        raise


def transcribe_audio(audio_path: str, model_dir: str) -> str:
    """Transcribe an audio file to text. Returns empty string on failure."""
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    try:
        model = _load_model(model_dir)
        segments, info = model.transcribe(
            audio_path,
            language="bn",
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
        logger.info(f"Transcribed ({info.language}, {info.language_probability:.2f}): {text[:80]}")
        return text
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""

import json
import logging
import os
import threading
from typing import Generator as TypeGenerator, List

import requests
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3.5:0.8b")
GENERATION_TIMEOUT = 90  # seconds


def format_sources(docs: List[Document]) -> List[str]:
    if not docs:
        return []
    sources = []
    for doc in docs:
        meta = doc.metadata or {}
        class_level = meta.get("class", "N/A")
        subject = meta.get("subject", "N/A")
        chapter_no = meta.get("chapter_no", "N/A")
        page_no = meta.get("page_no", "N/A")
        sources.append(f"{class_level} {subject} — Chapter {chapter_no}, Page: {page_no}")
    return list(dict.fromkeys(sources))


class Generator:

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._cancel_event = threading.Event()
        logger.info(f"[Generator] Ready — model: {self.model}")

    def cancel(self):
        self._cancel_event.set()

    def generate_stream(
        self,
        messages: list,
        docs: List[Document],
        include_sources: bool = True,
        file_path: str | None = None,
    ) -> TypeGenerator[dict, None, None]:

        self._cancel_event.clear()

        if not docs and not file_path:
            yield {"chunk": "I could not find relevant information to answer your question.\n\n"}
            yield {"sources": []}
            return

        # Map roles to Ollama format (user / assistant only)
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant"):
                role = "user"
            ollama_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {"temperature": 0.2},
        }

        try:
            with requests.post(
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
                stream=True,
                timeout=GENERATION_TIMEOUT,
            ) as resp:
                if resp.status_code != 200:
                    body = resp.text[:300]
                    logger.error(f"Ollama returned {resp.status_code}: {body}")
                    yield {"chunk": f"\n\nOllama error ({resp.status_code}): {body}"}
                    yield {"sources": []}
                    return

                for raw_line in resp.iter_lines():
                    if self._cancel_event.is_set():
                        logger.info("Generation cancelled by user")
                        break

                    if not raw_line:
                        continue

                    try:
                        # raw_line is bytes; decode to str first
                        line_str = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                        data = json.loads(line_str)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"Stream parse error: {e}")
                        continue

                    # Extract token text — MUST decode JSON field, not raw bytes
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield {"chunk": token}

                    if data.get("done"):
                        break

        except requests.exceptions.ConnectionError:
            logger.error("Cannot reach Ollama — is it running?")
            yield {"chunk": "\n\nCannot reach the local AI model. Please check that Ollama is running."}
        except requests.exceptions.Timeout:
            logger.error("Ollama generation timed out")
            yield {"chunk": "\n\nGeneration timed out. Try a shorter question or restart Ollama."}
        except Exception as e:
            logger.error(f"Generator error: {e}", exc_info=True)
            yield {"chunk": f"\n\nUnexpected error: {e}"}

        if include_sources:
            yield {"sources": format_sources(docs)}

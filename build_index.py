"""
build_index.py — Ingest raw_data/*.jsonl, embed via Ollama bge-m3, build FAISS + BM25.

Usage:
    python build_index.py                   # uses defaults
    python build_index.py --index-dir /path/to/index --data-dir /path/to/raw_data
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _format_chunk(item: dict) -> str:
    parts = [
        f"Class: {item.get('class', '')} - Subject: {item.get('subject', '')}",
        f"Chapter {item.get('chapter_no', '')}: {item.get('chapter_title', '')}",
        f"Page: {item.get('page_no', '')}",
        f"Topics: {', '.join(item.get('topic', []))}",
        f"Content:\n{item.get('content', '')}",
    ]
    return "\n".join(parts)


def build_index(index_dir: str, data_dir: str | None = None):
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from scripts.pipeline.retriever import OllamaEmbeddings

    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    raw_data = Path(data_dir) if data_dir else PROJECT_ROOT / "raw_data"
    if not raw_data.exists():
        raise FileNotFoundError(f"raw_data directory not found: {raw_data}")

    jsonl_files = sorted(raw_data.glob("*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {raw_data}")

    logger.info(f"Found {len(jsonl_files)} JSONL files in {raw_data}")

    all_docs: list[Document] = []
    for jf in jsonl_files:
        logger.info(f"  Reading {jf.name}...")
        try:
            with open(jf, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning(f"    Line {line_num}: JSON error — {e}")
                        continue
                    if "content" not in item:
                        continue
                    doc = Document(
                        page_content=_format_chunk(item),
                        metadata={
                            "chunk_id": item.get("chunk_id"),
                            "class": item.get("class"),
                            "subject": item.get("subject"),
                            "chapter_no": item.get("chapter_no"),
                            "chapter_title": item.get("chapter_title"),
                            "page_no": item.get("page_no"),
                            "source": item.get("chunk_id", f"{jf.name}:{line_num}"),
                            "source_file": jf.name,
                            "topic": item.get("topic"),
                        },
                    )
                    all_docs.append(doc)
        except Exception as e:
            logger.warning(f"  Could not read {jf.name}: {e}")

    if not all_docs:
        raise ValueError("No documents loaded — check raw_data/*.jsonl format")

    logger.info(f"Total documents: {len(all_docs)}")
    embeddings = OllamaEmbeddings()
    logger.info("Building FAISS vector store via Ollama bge-m3 (this may take several minutes)...")
    vector_store = FAISS.from_documents(all_docs, embeddings)
    vector_store.save_local(str(index_path))
    logger.info(f"FAISS index saved to {index_path}")
    logger.info("Index build complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Shikhbo FAISS+BM25 index")
    parser.add_argument("--index-dir", default=None, help="Where to save the index")
    parser.add_argument("--data-dir", default=None, help="Path to raw_data/ directory")
    args = parser.parse_args()

    if args.index_dir is None:
        from platformdirs import user_data_dir
        args.index_dir = str(Path(user_data_dir("shikhbo")) / "index")

    build_index(args.index_dir, args.data_dir)

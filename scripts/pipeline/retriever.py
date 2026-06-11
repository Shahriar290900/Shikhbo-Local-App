import json
import logging
import math
import os
import warnings
from collections import defaultdict
from pathlib import Path

import requests
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from rank_bm25 import BM25Okapi

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://127.0.0.1:11434"
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

VECTOR_WEIGHT = 0.6
BM25_WEIGHT = 0.4
TOP_K = 3
RRF_K = 60

# Index dir is set by app.py before Retriever is instantiated
_index_dir: Path | None = None


def set_index_dir(path: "str | Path"):
    global _index_dir
    _index_dir = Path(path)


def _matches_filter(metadata: dict, class_filter: str | None, subject_filter: str | None) -> bool:
    if class_filter and metadata.get("class", "").upper() != class_filter.upper():
        return False
    if subject_filter and metadata.get("subject", "").upper() != subject_filter.upper():
        return False
    return True


class OllamaEmbeddings(Embeddings):
    """Local Ollama bge-m3 embeddings — no internet required after model pull."""

    def __init__(self, model: str = EMBED_MODEL):
        self.model = model

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        try:
            resp = requests.post(
                f"{OLLAMA_BASE}/api/embed",
                json={"model": self.model, "input": [text]},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            vector = data["embeddings"][0]
            return self._l2_normalize([float(v) for v in vector])
        except Exception as e:
            logger.error(f"Embed error: {e}")
            raise

    @staticmethod
    def _l2_normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(x * x for x in vector))
        return vector if norm == 0 else [x / norm for x in vector]


class Retriever:
    def __init__(self, index_dir: "str | Path | None" = None):
        db_dir = Path(index_dir) if index_dir else _index_dir
        if not db_dir or not db_dir.exists():
            raise FileNotFoundError(f"Index directory not found: {db_dir}")

        self.embeddings = OllamaEmbeddings()
        logger.info("Loading FAISS index...")
        self.vector_store = FAISS.load_local(
            str(db_dir),
            embeddings=self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self._docs: list[Document] = list(self.vector_store.docstore._dict.values())
        logger.info(f"Loaded {len(self._docs)} documents")

        logger.info("Building BM25 index...")
        tokenized = [doc.page_content.lower().split() for doc in self._docs]
        self._bm25 = BM25Okapi(tokenized)
        logger.info("Retriever ready")

    def retrieve(
        self,
        query: str,
        class_filter: str | None = None,
        subject_filter: str | None = None,
    ) -> list[Document]:
        vector_hits = self._vector_search(query, class_filter, subject_filter)
        bm25_hits = self._bm25_search(query, class_filter, subject_filter)
        return self._fuse(vector_hits, bm25_hits)

    def _vector_search(self, query, class_filter, subject_filter) -> list[Document]:
        candidates = self.vector_store.similarity_search(query, k=TOP_K * 5)
        filtered = [d for d in candidates if _matches_filter(d.metadata, class_filter, subject_filter)]
        return filtered[:TOP_K]

    def _bm25_search(self, query, class_filter, subject_filter) -> list[Document]:
        scores = self._bm25.get_scores(query.lower().split()).tolist()
        scored = [
            (doc, score)
            for doc, score in zip(self._docs, scores)
            if _matches_filter(doc.metadata, class_filter, subject_filter)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:TOP_K]]

    def _fuse(self, vector_hits: list[Document], bm25_hits: list[Document]) -> list[Document]:
        scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, Document] = {}

        for rank, doc in enumerate(vector_hits, start=1):
            uid = doc.metadata.get("source", str(id(doc)))
            scores[uid] += VECTOR_WEIGHT / (RRF_K + rank)
            doc_map[uid] = doc

        for rank, doc in enumerate(bm25_hits, start=1):
            uid = doc.metadata.get("source", str(id(doc)))
            scores[uid] += BM25_WEIGHT / (RRF_K + rank)
            doc_map[uid] = doc

        top_uids = sorted(scores, key=scores.get, reverse=True)[:TOP_K]
        return [doc_map[uid] for uid in top_uids]

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_DEPTH = 5  # keep last 5 user+assistant pairs

_retriever = None
_generator = None
_prompts = None
_ctx_builder = None


def init_pipeline(index_dir: "str | Path"):
    """Load retriever and other singletons. Call once at startup."""
    global _retriever, _generator, _prompts, _ctx_builder

    from scripts.utils.prompts import Prompts
    from scripts.pipeline.generator import Generator
    from scripts.pipeline.retriever import Retriever
    from scripts.utils.context_builder import ContextBuilder

    _prompts = Prompts()
    _ctx_builder = ContextBuilder()
    _generator = Generator()

    try:
        _retriever = Retriever(index_dir=index_dir)
    except FileNotFoundError:
        logger.warning("Index not found — RAG will be disabled until index is built")
        _retriever = None


def run_pipeline_stream(user_json: dict):
    query = user_json.get("query", "")
    class_level = user_json.get("class_level", "SSC")
    subject = user_json.get("subject", "ICT")
    mode = user_json.get("mode") or "normal"
    curriculum = user_json.get("curriculum", "NCTB")
    messages = list(user_json.get("messages", []))
    file_path = user_json.get("file_path", None)

    # Lazy init if needed
    global _generator, _prompts, _ctx_builder
    if _generator is None:
        from scripts.pipeline.generator import Generator
        _generator = Generator()
    if _prompts is None:
        from scripts.utils.prompts import Prompts
        _prompts = Prompts()
    if _ctx_builder is None:
        from scripts.utils.context_builder import ContextBuilder
        _ctx_builder = ContextBuilder()

    yield {"status": "thinking"}

    # 1. Retrieve
    docs = []
    try:
        yield {"status": "retrieving"}
        if _retriever is not None:
            docs = _retriever.retrieve(query, class_filter=class_level, subject_filter=subject)
        else:
            logger.warning("Retriever not ready — answering without RAG context")
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        docs = []

    # 2. Build prompt
    has_file = bool(file_path)
    prompt_template = _prompts.get(
        query=query,
        class_level=class_level,
        subject=subject,
        curriculum=curriculum,
        mode=mode,
        has_file=has_file,
    )
    context_text = _ctx_builder.aggregate(docs) if docs else "No relevant context found."
    full_prompt = prompt_template.replace("{context}", context_text)

    # 3. Append current turn and trim to window
    messages.append({"role": "user", "content": full_prompt})
    max_msgs = MAX_DEPTH * 2
    if len(messages) > max_msgs:
        messages = messages[len(messages) - max_msgs:]

    yield {"status": "synthesizing"}

    # 4. Stream generation
    for payload in _generator.generate_stream(
        messages=messages,
        docs=docs,
        file_path=file_path,
    ):
        yield payload

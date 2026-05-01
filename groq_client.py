"""
Groq client with task-type-based model fallback chains.

TPD (tokens-per-day exhausted) → mark model exhausted, skip to next tier
RPM (requests-per-minute exceeded) → wait 5 s, retry same model
All tiers exhausted → raise RuntimeError with friendly message

Degradation state is stored in st.session_state when available (Streamlit context),
falling back to a module-level set for background threads.

Task types:
- light: web_search filtering/formatting (fast, simple tasks)
- standard: Router intent recognition (default)
- heavy: stock_analysis AI analysis (complex reasoning)
"""
import os
import time
from typing import Optional, List
from groq import Groq

# ── Task-type-based tier definitions ──────────────────────────────────────────

# Light tasks: web_search filtering/formatting
LIGHT_CHAIN = [
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
]

# Standard tasks: Router intent recognition (default)
STANDARD_CHAIN = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
]

# Heavy tasks: stock_analysis AI analysis
HEAVY_CHAIN = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

# Legacy default chain (for backward compatibility)
TIERS = STANDARD_CHAIN

# ── Singleton client ──────────────────────────────────────────────────────────

_client: Optional[Groq] = None


def _groq() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


# ── Exhausted model tracking ──────────────────────────────────────────────────

_module_exhausted: set = set()  # fallback for non-Streamlit contexts


def _exhausted() -> set:
    try:
        import streamlit as st
        if "exhausted_models" not in st.session_state:
            st.session_state.exhausted_models = set()
        return st.session_state.exhausted_models
    except Exception:
        return _module_exhausted


def _mark_exhausted(model: str) -> None:
    try:
        import streamlit as st
        if "exhausted_models" not in st.session_state:
            st.session_state.exhausted_models = set()
        st.session_state.exhausted_models.add(model)
    except Exception:
        _module_exhausted.add(model)


# ── Public API ────────────────────────────────────────────────────────────────

def _get_chain_for_task(task_type: str) -> List[str]:
    """Get the appropriate model chain for the given task type."""
    if task_type == "light":
        return LIGHT_CHAIN
    elif task_type == "heavy":
        return HEAVY_CHAIN
    else:  # "standard" or any other value
        return STANDARD_CHAIN


def get_model(task_type: str = "standard") -> str:
    """
    Return the highest-priority non-exhausted model for the given task type.
    
    Args:
        task_type: "light", "standard", or "heavy"
    """
    ex = _exhausted()
    chain = _get_chain_for_task(task_type)
    for tier in chain:
        if tier not in ex:
            return tier
    raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")


def chat_completion(messages: list, stream: bool = False, task_type: str = "standard", **kwargs):
    """
    Call Groq chat.completions.create with automatic tier fallback.

    Args:
        messages: Chat messages
        stream: Whether to stream the response
        task_type: "light", "standard", or "heavy" - determines model chain
        **kwargs: Additional arguments for chat.completions.create

    Do NOT pass `model` — it is managed internally based on task_type.
    Returns (response, warning_str).
      warning_str == "" when no fallback occurred.
      warning_str == "⚠️ 模型降级: <old> → <new>" when a tier was skipped.
    Raises RuntimeError if all tiers are exhausted.
    """
    kwargs.pop("model", None)  # ignore any accidental model kwarg

    client = _groq()
    chain = _get_chain_for_task(task_type)
    candidates = [t for t in chain if t not in _exhausted()]
    if not candidates:
        raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")

    original = candidates[0]
    warning = ""

    for model in candidates:
        while True:  # RPM retry loop for this tier
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=stream,
                    **kwargs,
                )
                if model != original:
                    warning = f"⚠️ 模型降级: {original} → {model}"
                return resp, warning
            except Exception as exc:
                err = str(exc)
                if "429" not in err:
                    raise
                if _is_rpm(err):
                    time.sleep(5)
                    continue  # retry same model after wait
                else:  # TPD or unknown 429
                    _mark_exhausted(model)
                    break  # move to next tier

    raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_rpm(err: str) -> bool:
    low = err.lower()
    return "requests per minute" in low or "rpm" in low

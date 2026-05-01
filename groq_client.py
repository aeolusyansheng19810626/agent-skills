"""
Groq client with 5-tier model fallback.

TPD (tokens-per-day exhausted) → mark model exhausted, skip to next tier
RPM (requests-per-minute exceeded) → wait 5 s, retry same model
All tiers exhausted → raise RuntimeError with friendly message

Degradation state is stored in st.session_state when available (Streamlit context),
falling back to a module-level set for background threads.
"""
import os
import time
from typing import Optional
from groq import Groq

# ── Tier definitions ──────────────────────────────────────────────────────────

TIER_TOP       = "openai/gpt-oss-120b"
TIER_UPPER_MID = "openai/gpt-oss-20b"
TIER_MID       = "qwen/qwen3-32b"
TIER_LOW       = "meta-llama/llama-4-scout-17b-16e-instruct"
TIER_DEBUG     = "llama-3.1-8b-instant"

TIERS = [TIER_TOP, TIER_UPPER_MID, TIER_MID, TIER_LOW, TIER_DEBUG]

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

def get_model() -> str:
    """Return the highest-priority non-exhausted model."""
    ex = _exhausted()
    for tier in TIERS:
        if tier not in ex:
            return tier
    raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")


def chat_completion(messages: list, stream: bool = False, **kwargs):
    """
    Call Groq chat.completions.create with automatic tier fallback.

    Do NOT pass `model` — it is managed internally.
    Returns (response, warning_str).
      warning_str == "" when no fallback occurred.
      warning_str == "⚠️ 模型降级: <old> → <new>" when a tier was skipped.
    Raises RuntimeError if all tiers are exhausted.
    """
    kwargs.pop("model", None)  # ignore any accidental model kwarg

    client = _groq()
    candidates = [t for t in TIERS if t not in _exhausted()]
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

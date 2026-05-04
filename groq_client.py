"""
タスクタイプベースのモデルフォールバックチェーンを持つGroqクライアント

TPD（1日あたりのトークン上限）→ モデルを使用済みとしてマーク、次の層へスキップ
RPM（1分あたりのリクエスト上限）→ 5秒待機、同じモデルで再試行
全層使用済み → わかりやすいメッセージでRuntimeErrorを発生

劣化状態はStreamlitコンテキストで利用可能な場合はst.session_stateに保存され、
バックグラウンドスレッドではモジュールレベルのセットにフォールバック。

タスクタイプ:
- light: web_search フィルタリング/フォーマット（高速、シンプルなタスク）
- standard: ルーターの意図認識（デフォルト）
- heavy: stock_analysis AI分析（複雑な推論）
"""
import os
import time
from typing import Optional, List
from groq import Groq

# ── タスクタイプベースの層定義 ────────────────────────────────────────────────

# 軽量タスク: web_search フィルタリング/フォーマット
LIGHT_CHAIN = [
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
]

# 標準タスク: ルーターの意図認識（デフォルト）
STANDARD_CHAIN = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
]

# 重量タスク: stock_analysis AI分析
HEAVY_CHAIN = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

# レガシーデフォルトチェーン（後方互換性のため）
TIERS = STANDARD_CHAIN

# ── シングルトンクライアント ──────────────────────────────────────────────────

_client: Optional[Groq] = None


def _groq() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


# ── 使用済みモデルの追跡 ──────────────────────────────────────────────────────

_module_exhausted: set = set()  # 非Streamlitコンテキスト用のフォールバック


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


# ── パブリックAPI ─────────────────────────────────────────────────────────────

def _get_chain_for_task(task_type: str) -> List[str]:
    """指定されたタスクタイプに適したモデルチェーンを取得"""
    if task_type == "light":
        return LIGHT_CHAIN
    elif task_type == "heavy":
        return HEAVY_CHAIN
    else:  # "standard" or any other value
        return STANDARD_CHAIN


def get_model(task_type: str = "standard") -> str:
    """
    指定されたタスクタイプの最優先で使用済みでないモデルを返す
    
    Args:
        task_type: "light"、"standard"、または"heavy"
    """
    ex = _exhausted()
    chain = _get_chain_for_task(task_type)
    for tier in chain:
        if tier not in ex:
            return tier
    raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")


def chat_completion(messages: list, stream: bool = False, task_type: str = "standard", **kwargs):
    """
    自動層フォールバックでGroq chat.completions.createを呼び出す

    Args:
        messages: チャットメッセージ
        stream: レスポンスをストリームするか
        task_type: "light"、"standard"、または"heavy" - モデルチェーンを決定
        **kwargs: chat.completions.createの追加引数

    `model`は渡さないこと — task_typeに基づいて内部で管理される。
    (response, warning_str)を返す。
      warning_str == "" フォールバックが発生しなかった場合
      warning_str == "⚠️ 模型降级: <old> → <new>" 層がスキップされた場合
    全層が使用済みの場合はRuntimeErrorを発生。
    """
    kwargs.pop("model", None)  # 誤ってmodelキーワード引数が渡された場合は無視

    client = _groq()
    chain = _get_chain_for_task(task_type)
    candidates = [t for t in chain if t not in _exhausted()]
    if not candidates:
        raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")

    original = candidates[0]
    warning = ""

    for model in candidates:
        while True:  # この層のRPM再試行ループ
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
                    continue  # 待機後に同じモデルで再試行
                else:  # TPDまたは不明な429
                    _mark_exhausted(model)
                    break  # 次の層へ移動

    raise RuntimeError("❌ 所有模型均已达到每日限额，请明天再试。")


# ── ヘルパー ──────────────────────────────────────────────────────────────────

def _is_rpm(err: str) -> bool:
    low = err.lower()
    return "requests per minute" in low or "rpm" in low

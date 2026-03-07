"""
通用 AI 聊天服务。

支持两种模式：
- free：自由聊天，不附加业务数据上下文；
- query_context：携带当前页面最新查询数据包，与用户进行连续对话。
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.services import ai_report_modes, ai_runtime

CHAT_MODE_FREE = "free"
CHAT_MODE_QUERY_CONTEXT = "query_context"
CHAT_SESSION_TTL_SECONDS = 30 * 60
CHAT_SESSION_MAX_TURNS = 20
CHAT_MAX_HISTORY_ITEMS = 12

_CHAT_SESSION_STORE: Dict[str, Dict[str, Any]] = {}
_CHAT_SESSION_LOCK = threading.Lock()


class AiChatContextPayload(BaseModel):
    title: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
    query: Dict[str, Any] = Field(default_factory=dict)
    rows: List[dict] = Field(default_factory=list)
    comparison_rows: List[dict] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)


class AiChatRequest(BaseModel):
    message: str
    mode: Literal["free", "query_context"] = CHAT_MODE_FREE
    session_id: Optional[str] = None
    history: List[dict] = Field(default_factory=list)
    context: Optional[AiChatContextPayload] = None


class AiChatResponse(BaseModel):
    ok: bool
    project_key: str
    mode: str
    session_id: str
    answer: str
    context_applied: bool = False


class AiChatDebugResponse(BaseModel):
    ok: bool
    project_key: str
    scope: str
    mode: str
    session_id: str
    context_applied: bool = False
    provider: str
    model: str
    base_url: str = ""
    history_count: int = 0
    input_message: str
    context_summary: Dict[str, Any] = Field(default_factory=dict)


def _scope_session_key(scope: str, session_id: str) -> str:
    return f"{scope}:{session_id}"


def _prune_sessions() -> None:
    cutoff = time.time() - CHAT_SESSION_TTL_SECONDS
    stale_keys = [
        key
        for key, payload in _CHAT_SESSION_STORE.items()
        if float((payload or {}).get("updated_at") or 0.0) < cutoff
    ]
    for key in stale_keys:
        _CHAT_SESSION_STORE.pop(key, None)


def normalize_chat_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw == CHAT_MODE_QUERY_CONTEXT:
        return CHAT_MODE_QUERY_CONTEXT
    return CHAT_MODE_FREE


def get_or_create_session(scope: str, session_id: Optional[str]) -> str:
    candidate = str(session_id or "").strip()
    if not candidate:
        candidate = uuid.uuid4().hex
    with _CHAT_SESSION_LOCK:
        _prune_sessions()
        key = _scope_session_key(scope, candidate)
        payload = _CHAT_SESSION_STORE.get(key)
        if not isinstance(payload, dict):
            payload = {"history": [], "updated_at": time.time()}
            _CHAT_SESSION_STORE[key] = payload
        else:
            payload["updated_at"] = time.time()
    return candidate


def get_session_history(scope: str, session_id: str, history: List[dict], max_turns: int = CHAT_SESSION_MAX_TURNS) -> List[dict]:
    merged_history: List[dict] = []
    provided = history if isinstance(history, list) else []
    for item in provided[-max_turns:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        merged_history.append({"role": role, "content": content})
    with _CHAT_SESSION_LOCK:
        key = _scope_session_key(scope, session_id)
        payload = _CHAT_SESSION_STORE.get(key) or {}
        stored = payload.get("history") if isinstance(payload, dict) else []
        if isinstance(stored, list):
            for item in stored[-max_turns:]:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "").strip().lower()
                content = str(item.get("content") or "").strip()
                if role not in {"user", "assistant"} or not content:
                    continue
                merged_history.append({"role": role, "content": content})
    return merged_history[-max_turns:]


def append_session_history(scope: str, session_id: str, user_message: str, assistant_message: str) -> None:
    with _CHAT_SESSION_LOCK:
        _prune_sessions()
        key = _scope_session_key(scope, session_id)
        payload = _CHAT_SESSION_STORE.get(key)
        if not isinstance(payload, dict):
            payload = {"history": [], "updated_at": time.time()}
            _CHAT_SESSION_STORE[key] = payload
        history = payload.get("history")
        if not isinstance(history, list):
            history = []
            payload["history"] = history
        history.extend(
            [
                {"role": "user", "content": str(user_message or "").strip()},
                {"role": "assistant", "content": str(assistant_message or "").strip()},
            ]
        )
        payload["history"] = history[-CHAT_SESSION_MAX_TURNS:]
        payload["updated_at"] = time.time()


def _trim_scalar(value: Any, max_len: int = 300) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}…"


def _trim_rows(rows: List[dict], max_rows: int, max_columns: int = 12) -> List[dict]:
    safe_rows: List[dict] = []
    for row in (rows if isinstance(rows, list) else [])[:max_rows]:
        if not isinstance(row, dict):
            continue
        trimmed: Dict[str, Any] = {}
        for idx, (key, value) in enumerate(row.items()):
            if idx >= max_columns:
                break
            trimmed[str(key)] = _trim_scalar(value, 120)
        safe_rows.append(trimmed)
    return safe_rows


def summarize_query_context(context: Optional[AiChatContextPayload]) -> Dict[str, Any]:
    payload = context if isinstance(context, AiChatContextPayload) else None
    if payload is None:
        return {}
    summary = {
        "title": str(payload.title or "").strip(),
        "meta": {str(key): _trim_scalar(value, 160) for key, value in (payload.meta or {}).items()},
        "query": {str(key): _trim_scalar(value, 160) for key, value in (payload.query or {}).items()},
        "row_count": len(payload.rows or []),
        "comparison_row_count": len(payload.comparison_rows or []),
        "rows_preview": _trim_rows(payload.rows or [], max_rows=12),
        "comparison_rows_preview": _trim_rows(payload.comparison_rows or [], max_rows=8),
        "warnings": [str(item or "").strip() for item in (payload.warnings or []) if str(item or "").strip()][:8],
        "extras": {str(key): _trim_scalar(value, 240) for key, value in (payload.extras or {}).items()},
    }
    return summary


def _serialize_context_summary(summary: Dict[str, Any]) -> str:
    char_limit = max(8000, int(ai_report_modes.resolve_prompt_data_char_limit() * 0.45))
    rows_limit = 12
    compare_limit = 8
    last_text = "{}"
    while rows_limit >= 3:
        candidate = dict(summary)
        candidate["rows_preview"] = list((summary.get("rows_preview") or [])[:rows_limit])
        candidate["comparison_rows_preview"] = list((summary.get("comparison_rows_preview") or [])[:compare_limit])
        text = json.dumps(candidate, ensure_ascii=False)
        last_text = text
        if len(text) <= char_limit:
            return text
        rows_limit -= 3
        compare_limit = max(2, compare_limit - 2)
    return last_text[:char_limit]


def _format_history_messages(history: List[dict]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    for item in history[-CHAT_MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": content})
    return messages


def build_chat_messages(
    mode: str, 
    user_message: str, 
    history: List[dict], 
    context_summary: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    normalized_mode = normalize_chat_mode(mode)
    
    # 1. System Message
    system_content = "你是一个专业的在线数据填报与分析助手，正在凤凰计划 (Phoenix Plan) 应用中为用户提供服务。"
    if normalized_mode == CHAT_MODE_QUERY_CONTEXT:
        context_text = _serialize_context_summary(context_summary or {})
        system_content += (
            "\n当前处于“数据分析对话”模式。以下是页面最新的查询结果摘要（JSON格式）：\n"
            f"{context_text}\n"
            "请优先基于上述数据回答。如果数据不足以支持结论，请明确告知用户，不要编造。"
        )
    else:
        system_content += "\n当前处于“自由对话”模式，请直接与用户进行自然、连贯的中文对话。"
    
    messages.append({"role": "system", "content": system_content})

    # 2. History Messages
    messages.extend(_format_history_messages(history))

    # 3. User Message
    messages.append({"role": "user", "content": str(user_message or "").strip()})
    
    return messages


def run_chat_turn(project_key: str, scope: str, payload: AiChatRequest) -> AiChatResponse:
    user_message = str(payload.message or "").strip()
    if not user_message:
        raise ValueError("message 不能为空")
    mode = normalize_chat_mode(payload.mode)
    session_id = get_or_create_session(scope, payload.session_id)
    history = get_session_history(scope, session_id, payload.history)
    context_applied = False
    context_summary: Dict[str, Any] = {}
    if mode == CHAT_MODE_QUERY_CONTEXT:
        if payload.context is None:
            raise ValueError("query_context 模式需要 context 数据包")
        context_summary = summarize_query_context(payload.context)
        if int(context_summary.get("row_count") or 0) <= 0 and int(context_summary.get("comparison_row_count") or 0) <= 0:
            raise ValueError("当前页面暂无可用查询结果，请先执行查询")
        context_applied = True

    messages = build_chat_messages(mode, user_message, history, context_summary=context_summary)
    answer = str(ai_runtime.call_chat_model(messages, retries=2) or "").strip()
    if not answer:
        answer = "我暂时没有生成可用回复，请稍后重试。"
    append_session_history(scope, session_id, user_message, answer)
    return AiChatResponse(
        ok=True,
        project_key=project_key,
        mode=mode,
        session_id=session_id,
        answer=answer,
        context_applied=context_applied,
    )


def build_chat_debug_payload(project_key: str, scope: str, payload: AiChatRequest) -> AiChatDebugResponse:
    user_message = str(payload.message or "").strip()
    if not user_message:
        raise ValueError("message 不能为空")
    mode = normalize_chat_mode(payload.mode)
    session_id = get_or_create_session(scope, payload.session_id)
    history = get_session_history(scope, session_id, payload.history)
    context_applied = False
    context_summary: Dict[str, Any] = {}
    if mode == CHAT_MODE_QUERY_CONTEXT:
        if payload.context is None:
            raise ValueError("query_context 模式需要 context 数据包")
        context_summary = summarize_query_context(payload.context)
        if int(context_summary.get("row_count") or 0) <= 0 and int(context_summary.get("comparison_row_count") or 0) <= 0:
            raise ValueError("当前页面暂无可用查询结果，请先执行查询")
        context_applied = True
    settings = ai_runtime.load_ai_provider_settings()
    return AiChatDebugResponse(
        ok=True,
        project_key=project_key,
        scope=scope,
        mode=mode,
        session_id=session_id,
        context_applied=context_applied,
        provider=str(settings.get("provider") or ""),
        model=str(settings.get("model") or ""),
        base_url=str(settings.get("base_url") or ""),
        history_count=len(history),
        input_message=user_message,
        context_summary=context_summary,
    )

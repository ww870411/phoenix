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
QUERY_CONTEXT_SYSTEM_PROMPT = """你现在是一位资深的能源供热企业经济运行部数据分析专家。我们集团是一家热电联产企业，有多家热电厂和供暖锅炉房。不同口径代表含义如下：全口径是集团所有口径的汇总情况，主城区包括了主城区范围内的北海热电厂（包含两个部分，即北海和北海水炉，前者既发电又产热，后者只产热）、香海热电厂及其统一的供热公司（两个电厂只生产，供热公司只供暖并负责调度），另外，主城区电锅炉也是主城区内的一个独立口径。在主城区中，从股权的角度，还可以分为集团本部和股份本部，香海热电厂和供热公司属于集团本部，北海热电厂和主城区电锅炉属于股份本部，它们之间会有关联交易。金州热电北方热电是主城区外的两家兼具热电联产和供暖的企业。金普庄河是主城区外的两家锅炉房纯供暖企业，后者2025年11月份起部分接入了该市的热力主管网，实行购热供暖。研究院是主城区外的一家电锅炉供暖企业。"""

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


def _trim_rows(rows: List[dict], max_rows: int, max_columns: int = 32) -> List[dict]:
    safe_rows: List[dict] = []
    for row in (rows if isinstance(rows, list) else [])[:max_rows]:
        if not isinstance(row, dict):
            continue
        trimmed: Dict[str, Any] = {}
        # 排除一些对 AI 无用的元数据字段，节省 Token
        excluded_keys = {"id", "project_key", "sheet_key", "biz_date", "created_at", "updated_at"}
        count = 0
        for key, value in row.items():
            k_str = str(key)
            if k_str in excluded_keys:
                continue
            if count >= max_columns:
                break
            trimmed[k_str] = _trim_scalar(value, 160)
            count += 1
        safe_rows.append(trimmed)
    return safe_rows


def summarize_query_context(context: Optional[AiChatContextPayload]) -> Dict[str, Any]:
    payload = context if isinstance(context, AiChatContextPayload) else None
    if payload is None:
        return {}
    summary = {
        "title": str(payload.title or "").strip(),
        "meta": {str(key): _trim_scalar(value, 200) for key, value in (payload.meta or {}).items()},
        "query": {str(key): _trim_scalar(value, 200) for key, value in (payload.query or {}).items()},
        "row_count": len(payload.rows or []),
        "comparison_row_count": len(payload.comparison_rows or []),
        "rows_full": _trim_rows(payload.rows or [], max_rows=max(1, len(payload.rows or [])), max_columns=24),
        "comparison_rows_full": _trim_rows(payload.comparison_rows or [], max_rows=max(1, len(payload.comparison_rows or [])), max_columns=24),
        "warnings": [str(item or "").strip() for item in (payload.warnings or []) if str(item or "").strip()][:10],
        "extras": {str(key): _trim_scalar(value, 300) for key, value in (payload.extras or {}).items()},
    }
    return summary


def _rows_to_compact_table(rows: List[dict], label: str) -> str:
    """将 JSON 列表转换为极致紧凑的类 CSV 表格格式。"""
    if not rows:
        return ""
    # 提取所有出现的 key（保持顺序）
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    
    lines = [f"--- {label} (Headers: {', '.join(keys)}) ---"]
    for r in rows:
        values = [str(r.get(k, "")) for k in keys]
        lines.append("|".join(values))
    
    return "\n".join(lines)


def _serialize_context_summary(summary: Dict[str, Any]) -> str:
    """
    将摘要序列化为紧凑字符串，优先使用表格格式以节省 Token。
    """
    # 提升上限到 24,000 字符，月报全量查询需要更大的胃口
    char_limit = max(24000, int(ai_report_modes.resolve_prompt_data_char_limit() * 0.8))
    
    # 提取非行数据部分
    base_info = {k: v for k, v in summary.items() if k not in ("rows_full", "comparison_rows_full")}
    
    rows_data = list(summary.get("rows_full") or [])
    comp_data = list(summary.get("comparison_rows_full") or [])
    
    rows_limit = len(rows_data)
    comp_limit = len(comp_data)

    while rows_limit >= 0:
        # 构造表格文本
        rows_table = _rows_to_compact_table(rows_data[:rows_limit], "Primary Data")
        comp_table = _rows_to_compact_table(comp_data[:comp_limit], "Comparison Data")
        
        # 组装最终文本
        parts = [
            "Metadata & Query Summary:",
            json.dumps(base_info, ensure_ascii=False, indent=2),
            rows_table,
            comp_table
        ]
        final_text = "\n\n".join(p for p in parts if p)
        
        if len(final_text) <= char_limit:
            return final_text
            
        # 逐步缩减行数
        if rows_limit > 5:
            rows_limit = int(rows_limit * 0.8)
            comp_limit = int(comp_limit * 0.8)
        else:
            rows_limit -= 1
            comp_limit = max(0, comp_limit - 1)
            
    return "Data too large to summarize."


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
        system_content = (
            f"{QUERY_CONTEXT_SYSTEM_PROMPT}\n"
            "当前处于“基于查询数据的连续对话”模式。以下是页面最新查询结果的 JSON 摘要：\n"
            f"{context_text}\n"
            "请严格基于上述数据回答；如果数据不足以支持结论，请明确告知用户，不要编造。"
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

"""
通用 AI 运行时服务。

职责：
- 读取并解析全局 AI Provider 配置；
- 缓存当前生效模型客户端；
- 提供统一的模型调用与连接测试能力；
- 为聊天工具、Agent 工具、报告服务提供可复用的底层入口。
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from backend.config import DATA_DIRECTORY
from backend.services.api_key_cipher import decrypt_api_key
from backend.services.project_data_paths import resolve_global_ai_settings_path

DATA_ROOT = Path(DATA_DIRECTORY)
GLOBAL_AI_SETTINGS_PATH = resolve_global_ai_settings_path()

_logger = logging.getLogger(__name__)
_runtime_client: Optional[Dict[str, Any]] = None
_runtime_signature: Optional[str] = None
_runtime_model_name: Optional[str] = None


def reset_runtime_client() -> None:
    """清空已缓存的 AI 客户端实例，确保下次调用重新读取配置。"""

    global _runtime_client, _runtime_signature, _runtime_model_name
    _runtime_client = None
    _runtime_signature = None
    _runtime_model_name = None


def safe_read_settings_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def load_effective_ai_settings() -> Dict[str, Any]:
    return safe_read_settings_json(GLOBAL_AI_SETTINGS_PATH)


def normalize_provider(value: Any) -> str:
    provider = str(value or "gemini").strip().lower()
    return provider if provider in {"gemini", "newapi"} else "gemini"


def decode_api_key(raw_value: Any) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""
    decoded = decrypt_api_key(text)
    if text.startswith("sk-") and not decoded.startswith("sk-"):
        return text
    if text.startswith("AIza") and not decoded.startswith("AIza"):
        return text
    return decoded


def resolve_active_provider_record(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    providers_raw = data.get("providers")
    if not isinstance(providers_raw, list) or not providers_raw:
        return None
    records: List[Dict[str, Any]] = []
    for idx, raw in enumerate(providers_raw):
        if not isinstance(raw, dict):
            continue
        kind = normalize_provider(raw.get("kind") or raw.get("provider"))
        provider_id = str(raw.get("id") or "").strip() or f"provider_{idx + 1}"
        api_keys_raw = raw.get("api_keys")
        encrypted_keys = api_keys_raw if isinstance(api_keys_raw, list) else []
        keys = [decode_api_key(key) for key in encrypted_keys if str(key or "").strip()]
        records.append(
            {
                "id": provider_id,
                "name": str(raw.get("name") or "").strip(),
                "kind": kind,
                "base_url": str(raw.get("base_url") or "").strip(),
                "model": str(raw.get("model") or "").strip(),
                "api_keys": keys,
            }
        )
    if not records:
        return None
    active_id = str(data.get("active_provider_id") or "").strip()
    if active_id:
        hit = next((record for record in records if str(record.get("id") or "") == active_id), None)
        if hit:
            return hit
    return records[0]


def load_gemini_settings(data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if data is None:
        data = load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")

    raw_keys = data.get("gemini_api_keys")
    api_key = ""
    if isinstance(raw_keys, list) and raw_keys:
        first_raw = str(raw_keys[0] or "")
        if first_raw:
            api_key = decode_api_key(first_raw)

    if not api_key:
        raw_single_key = data.get("gemini_api_key")
        if raw_single_key:
            api_key = decode_api_key(str(raw_single_key))

    model = data.get("gemini_model")
    if not api_key or not isinstance(api_key, str):
        raise RuntimeError("缺少有效的 gemini_api_key 配置 (请检查 gemini_api_keys 列表)")
    if not model or not isinstance(model, str):
        raise RuntimeError("缺少 gemini_model 配置")
    return {"api_key": api_key, "model": model}


def load_newapi_settings(data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if data is None:
        data = load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")

    base_url = str(data.get("newapi_base_url") or "").strip()
    if not base_url:
        raise RuntimeError("缺少 newapi_base_url 配置")
    model = str(data.get("newapi_model") or "").strip()
    if not model:
        raise RuntimeError("缺少 newapi_model 配置")

    raw_keys = data.get("newapi_api_keys")
    api_key = ""
    if isinstance(raw_keys, list) and raw_keys:
        first_raw = str(raw_keys[0] or "")
        if first_raw:
            api_key = decode_api_key(first_raw)

    if not api_key:
        raw_single_key = data.get("newapi_api_key")
        if raw_single_key:
            api_key = decode_api_key(str(raw_single_key))
    if not api_key:
        raise RuntimeError("缺少有效的 newapi_api_key 配置 (请检查 newapi_api_keys 列表)")
    return {"api_key": api_key, "model": model, "base_url": base_url}


def load_ai_provider_settings() -> Dict[str, Any]:
    data = load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")
    active_record = resolve_active_provider_record(data)
    if active_record is not None:
        provider = normalize_provider(active_record.get("kind"))
        api_keys = active_record.get("api_keys") or []
        api_key = str(api_keys[0] or "").strip() if isinstance(api_keys, list) and api_keys else ""
        model = str(active_record.get("model") or "").strip()
        if not api_key:
            raise RuntimeError("当前生效 Provider 缺少 API Key")
        if not model:
            raise RuntimeError("当前生效 Provider 缺少模型名")
        if provider == "newapi":
            base_url = str(active_record.get("base_url") or "").strip()
            if not base_url:
                raise RuntimeError("当前生效 New API Provider 缺少 Base URL")
            return {
                "provider": "newapi",
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
            }
        return {
            "provider": "gemini",
            "api_key": api_key,
            "model": model,
        }

    provider = normalize_provider(data.get("provider"))
    settings: Dict[str, Any]
    if provider == "newapi":
        settings = load_newapi_settings(data)
    else:
        settings = load_gemini_settings(data)
    settings["provider"] = provider
    return settings


def current_provider() -> str:
    try:
        data = load_effective_ai_settings()
        active_record = resolve_active_provider_record(data)
        if active_record is not None:
            return normalize_provider(active_record.get("kind"))
        return normalize_provider(data.get("provider"))
    except Exception:  # pylint: disable=broad-except
        return "gemini"


def extract_retry_delay_seconds(error_text: str) -> int:
    if not error_text:
        return 20
    candidates: List[int] = []
    match_retry_in = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_text, flags=re.IGNORECASE)
    if match_retry_in:
        try:
            candidates.append(int(math.ceil(float(match_retry_in.group(1)))))
        except (TypeError, ValueError):
            pass
    match_retry_block = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_text, flags=re.IGNORECASE)
    if match_retry_block:
        try:
            candidates.append(int(match_retry_block.group(1)))
        except (TypeError, ValueError):
            pass
    return max([20, *candidates])


def is_quota_or_rate_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    if "429" in text:
        return True
    keywords = [
        "quota exceeded",
        "rate limit",
        "resource has been exhausted",
        "generatecontentinputtokenspermodelperminute",
    ]
    return any(word in text for word in keywords)


def is_transient_gateway_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    transient_tokens = [
        "http 500",
        "http 502",
        "http 503",
        "http 504",
        "gateway time-out",
        "gateway timeout",
        "timed out",
        "connection reset",
    ]
    return any(token in text for token in transient_tokens)


def extract_response_text(response: Any) -> str:
    text = (response.text or "").strip() if response else ""
    if text:
        return text
    if response and getattr(response, "candidates", None):
        parts = []
        for candidate in response.candidates:
            for part in getattr(candidate, "content", {}).parts or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    parts.append(part_text)
        text = "\n".join(parts).strip()
    return text


def extract_newapi_response_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    part_text = item.get("text")
                    if isinstance(part_text, str):
                        parts.append(part_text)
            text = "\n".join(part for part in parts if part).strip()
            if text:
                return text
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        text = output_text.strip()
        if text:
            return text
    return ""


def build_newapi_chat_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise RuntimeError("newapi_base_url 不能为空")
    lower = normalized.lower()
    if lower.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def call_newapi_chat(
    prompt: Optional[str] = None,
    settings: Dict[str, Any] = None,
    timeout_seconds: int = 120,
    messages: Optional[List[Dict[str, str]]] = None
) -> str:
    url = build_newapi_chat_url(str(settings.get("base_url") or ""))
    
    if messages:
        chat_messages = messages
    else:
        chat_messages = [{"role": "user", "content": str(prompt or "")}]

    request_body = {
        "model": str(settings.get("model") or ""),
        "messages": chat_messages,
    }
    request_data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phoenix-AI-Client/1.0",
            "Authorization": f"Bearer {str(settings.get('api_key') or '')}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        if exc.code == 403 and "1010" in detail:
            raise RuntimeError(
                "New API 调用失败: HTTP 403 error code 1010（网关拒绝）。"
                f"请检查 base_url 是否为 API 域名与接口路径，当前请求地址: {url}。"
                "若该服务有防火墙/来源限制，请放行服务端请求。"
            ) from exc
        raise RuntimeError(f"New API 调用失败: HTTP {exc.code} {detail} (url={url})") from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(f"New API 调用失败: {exc}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"New API 返回内容不是有效 JSON: {raw_text[:300]}") from exc
    text = extract_newapi_response_text(payload if isinstance(payload, dict) else {})
    if not text:
        raise RuntimeError("New API 未返回有效文本内容")
    return text


def test_gemini_connection(api_key: str, model: str) -> Dict[str, Any]:
    if not api_key:
        raise RuntimeError("Gemini API Key 不能为空")
    if not model:
        raise RuntimeError("Gemini 模型不能为空")
    genai.configure(api_key=api_key)
    runtime_model = genai.GenerativeModel(model)
    response = runtime_model.generate_content("请仅回复: ok")
    text = extract_response_text(response)
    if not text:
        raise RuntimeError("Gemini 测试调用成功但未返回文本")
    return {"provider": "gemini", "model": model, "message": text[:120]}


def test_newapi_connection(base_url: str, api_key: str, model: str) -> Dict[str, Any]:
    if not base_url:
        raise RuntimeError("New API Base URL 不能为空")
    if not api_key:
        raise RuntimeError("New API Key 不能为空")
    if not model:
        raise RuntimeError("New API 模型不能为空")
    text = call_newapi_chat(
        "请仅回复: ok",
        {"base_url": base_url, "api_key": api_key, "model": model},
        timeout_seconds=60,
    )
    return {"provider": "newapi", "model": model, "message": text[:120]}


def run_ai_connection_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    active_record = resolve_active_provider_record(payload if isinstance(payload, dict) else {})
    if active_record is not None:
        provider = normalize_provider(active_record.get("kind"))
        keys = active_record.get("api_keys") or []
        first_key = str(keys[0] or "").strip() if isinstance(keys, list) and keys else ""
        model = str(active_record.get("model") or "").strip()
        if provider == "newapi":
            return test_newapi_connection(
                str(active_record.get("base_url") or "").strip(),
                first_key,
                model,
            )
        return test_gemini_connection(first_key, model)

    provider = normalize_provider(payload.get("provider"))
    if provider == "newapi":
        newapi_keys = payload.get("newapi_api_keys")
        first_key = ""
        if isinstance(newapi_keys, list) and newapi_keys:
            first_key = str(newapi_keys[0] or "").strip()
        return test_newapi_connection(
            str(payload.get("newapi_base_url") or "").strip(),
            first_key,
            str(payload.get("newapi_model") or "").strip(),
        )
    gemini_keys = payload.get("api_keys")
    first_key = ""
    if isinstance(gemini_keys, list) and gemini_keys:
        first_key = str(gemini_keys[0] or "").strip()
    return test_gemini_connection(
        first_key,
        str(payload.get("model") or "").strip(),
    )


def current_runtime_model_name() -> str:
    return str(_runtime_model_name or "")


def get_runtime_client() -> Dict[str, Any]:
    global _runtime_client, _runtime_signature, _runtime_model_name
    settings = load_ai_provider_settings()
    provider = str(settings.get("provider") or "gemini")
    signature_parts = [provider, str(settings.get("model") or "")]
    if provider == "newapi":
        signature_parts.append(str(settings.get("base_url") or ""))
    signature_parts.append(str(settings.get("api_key") or "")[:12])
    signature = "|".join(signature_parts)
    if _runtime_client is not None and _runtime_signature == signature:
        return _runtime_client

    if provider == "newapi":
        _runtime_client = {
            "provider": "newapi",
            "api_key": str(settings.get("api_key") or ""),
            "base_url": str(settings.get("base_url") or ""),
            "model": str(settings.get("model") or ""),
        }
        _runtime_model_name = str(settings.get("model") or "")
    else:
        genai.configure(api_key=str(settings.get("api_key") or ""))
        model_name = str(settings.get("model") or "")
        _runtime_client = {
            "provider": "gemini",
            "model": model_name,
            "client": genai.GenerativeModel(model_name),
        }
        _runtime_model_name = model_name
    _runtime_signature = signature
    return _runtime_client


def call_model(prompt: str, retries: int = 3) -> str:
    """旧版单文本调用封装。"""
    return call_chat_model([{"role": "user", "content": prompt}], retries=retries)


def call_chat_model(messages: List[Dict[str, str]], retries: int = 3) -> str:
    """
    通用多轮对话调用。
    
    参数:
    - messages: [{"role": "system/user/assistant", "content": "..."}]
    """
    runtime = get_runtime_client()
    provider = str(runtime.get("provider") or "gemini")
    last_error: Optional[Exception] = None

    for attempt in range(1, max(1, retries) + 1):
        try:
            if provider == "newapi":
                text = call_newapi_chat(settings=runtime, messages=messages)
            else:
                model = runtime.get("client")
                contents = []
                system_instruction = None
                for m in messages:
                    role = m.get("role")
                    content = m.get("content")
                    if role == "system":
                        system_instruction = content
                    else:
                        gemini_role = "user" if role == "user" else "model"
                        contents.append({"role": gemini_role, "parts": [content]})
                
                if system_instruction:
                    if contents:
                        contents[0]["parts"][0] = f"{system_instruction}\n\n{contents[0]['parts'][0]}"
                    else:
                        contents.append({"role": "user", "parts": [system_instruction]})

                response = model.generate_content(contents)
                text = extract_response_text(response)
            
            if not text:
                raise RuntimeError("模型未返回内容")
            return text
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if is_quota_or_rate_error(exc) and attempt < retries:
                delay_seconds = extract_retry_delay_seconds(str(exc))
                _logger.warning(
                    "%s 限流/配额触发，第 %s/%s 次调用失败，%s 秒后自动重试：%s",
                    provider,
                    attempt,
                    retries,
                    delay_seconds,
                    exc,
                )
                time.sleep(delay_seconds)
                continue
            if is_transient_gateway_error(exc) and attempt < retries:
                _logger.warning(
                    "%s 网关/超时错误，第 %s/%s 次调用失败，2 秒后重试：%s",
                    provider,
                    attempt,
                    retries,
                    exc,
                )
                time.sleep(2)
                continue
            raise
    raise RuntimeError(f"模型调用失败: {last_error}")


__all__ = [
    "GLOBAL_AI_SETTINGS_PATH",
    "current_provider",
    "current_runtime_model_name",
    "call_model",
    "call_chat_model",
    "call_newapi_chat",
    "build_newapi_chat_url",
    "decode_api_key",
    "extract_newapi_response_text",
    "extract_response_text",
    "extract_retry_delay_seconds",
    "get_runtime_client",
    "is_quota_or_rate_error",
    "is_transient_gateway_error",
    "load_ai_provider_settings",
    "load_effective_ai_settings",
    "load_gemini_settings",
    "load_newapi_settings",
    "normalize_provider",
    "reset_runtime_client",
    "resolve_active_provider_record",
    "run_ai_connection_test",
    "safe_read_settings_json",
    "test_gemini_connection",
    "test_newapi_connection",
]

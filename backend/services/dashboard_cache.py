# -*- coding: utf-8 -*-
"""
数据看板缓存管理。

职责：
- 统一管理 backend_data/dashboard_cache.json 的读写与结构约束；
- 为 API 层提供获取缓存、批量刷新、禁用等操作；
- 基于 date.json 中的 set_biz_date 生成默认缓存窗口（set_biz_date 及前两日）。
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Tuple

from backend.config import DATA_DIRECTORY
from backend.services.dashboard_expression import load_default_push_date, normalize_show_date

DATA_ROOT = Path(DATA_DIRECTORY)
CACHE_FILE = DATA_ROOT / "dashboard_cache.json"
CACHE_LOCK = Lock()
DEFAULT_CACHE_KEY = "__default__"
EAST_8 = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(EAST_8).isoformat()


def _default_bundle(project_key: str) -> Dict[str, Any]:
    return {
        "project_key": project_key,
        "disabled": False,
        "items": {},
        "updated_at": None,
    }


def _sanitize_items(items: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(items, dict):
        return {}
    sanitized: Dict[str, Dict[str, Any]] = {}
    for key, payload in items.items():
        if not isinstance(key, str):
            continue
        if not isinstance(payload, dict):
            continue
        sanitized[key] = deepcopy(payload)
    return sanitized


def _load_bundle(project_key: str) -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return _default_bundle(project_key)
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_bundle(project_key)

    if not isinstance(raw, dict):
        return _default_bundle(project_key)

    bundle = _default_bundle(project_key)
    if raw.get("project_key") not in (None, project_key):
        return bundle

    bundle["project_key"] = project_key
    bundle["disabled"] = bool(raw.get("disabled", False))
    bundle["updated_at"] = raw.get("updated_at")
    bundle["items"] = _sanitize_items(raw.get("items"))
    return bundle


def _write_bundle(bundle: Dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_FILE.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(CACHE_FILE)


def resolve_cache_key(show_date: str) -> str:
    """
    将请求中的 show_date 转换为缓存键。
    空字符串使用 DEFAULT_CACHE_KEY。
    """
    normalized = normalize_show_date(show_date)
    if normalized:
        return normalized
    return DEFAULT_CACHE_KEY


def get_cache_status(project_key: str) -> Dict[str, Any]:
    with CACHE_LOCK:
        bundle = _load_bundle(project_key)
    available_dates = sorted(
        date_key for date_key in bundle["items"].keys() if date_key != DEFAULT_CACHE_KEY
    )
    return {
        "disabled": bundle["disabled"],
        "available_dates": available_dates,
        "updated_at": bundle["updated_at"],
    }


def get_cached_payload(project_key: str, cache_key: str) -> Tuple[Dict[str, Any] | None, Dict[str, Any]]:
    """
    返回 (payload, status)。当缓存被禁用或不存在时，payload 为 None。
    """
    with CACHE_LOCK:
        bundle = _load_bundle(project_key)
        if bundle["disabled"]:
            payload = None
        else:
            payload = deepcopy(bundle["items"].get(cache_key))
        status = {
            "disabled": bundle["disabled"],
            "available_dates": sorted(
                key for key in bundle["items"].keys() if key != DEFAULT_CACHE_KEY
            ),
            "updated_at": bundle["updated_at"],
        }
    return payload, status


def update_cache_entry(project_key: str, cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with CACHE_LOCK:
        bundle = _load_bundle(project_key)
        bundle["disabled"] = False
        bundle["items"][cache_key] = deepcopy(payload)
        bundle["updated_at"] = _now_iso()
        _write_bundle(bundle)
    return {
        "disabled": False,
        "available_dates": sorted(
            key for key in bundle["items"].keys() if key != DEFAULT_CACHE_KEY
        ),
        "updated_at": bundle["updated_at"],
    }


def replace_cache(project_key: str, entries: Dict[str, Dict[str, Any]], disabled: bool = False) -> Dict[str, Any]:
    sanitized_entries = {
        key: deepcopy(value)
        for key, value in entries.items()
        if isinstance(key, str) and isinstance(value, dict)
    }
    with CACHE_LOCK:
        bundle = _default_bundle(project_key)
        bundle["disabled"] = bool(disabled)
        bundle["items"] = sanitized_entries if not bundle["disabled"] else {}
        bundle["updated_at"] = _now_iso()
        _write_bundle(bundle)
    return get_cache_status(project_key)


def disable_cache(project_key: str) -> Dict[str, Any]:
    return replace_cache(project_key, {}, disabled=True)


def default_publish_dates(window: int = 7) -> List[str]:
    """
    返回 set_biz_date 及其前 window-1 日（共 window 个日期），按时间升序排列。
    """
    base_iso = load_default_push_date()
    base_date = date.fromisoformat(base_iso)
    offsets = list(range(window - 1, -1, -1))
    ordered = [(base_date - timedelta(days=offset)).isoformat() for offset in offsets]
    # 去重（避免 window=1 时重复）
    seen = set()
    result: List[str] = []
    for item in ordered:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def summarize_cache(project_key: str) -> Dict[str, Any]:
    return get_cache_status(project_key)


def cache_keys_from_dates(dates: Iterable[str]) -> List[str]:
    keys: List[str] = []
    for value in dates:
        normalized = normalize_show_date(value)
        if normalized:
            keys.append(normalized)
    return keys


__all__ = [
    "DEFAULT_CACHE_KEY",
    "cache_keys_from_dates",
    "default_publish_dates",
    "disable_cache",
    "get_cache_status",
    "get_cached_payload",
    "replace_cache",
    "resolve_cache_key",
    "summarize_cache",
    "update_cache_entry",
]

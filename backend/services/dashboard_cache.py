"""数据看板缓存服务。

职责：
1. 兼容读取旧版单文件缓存 `dashboard_cache.json`；
2. 将缓存迁移到按日期目录拆分的新结构 `dashboard_cache_v2/`；
3. 抽取跨日期共享的静态数据，减少多日缓存重复写入。
"""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Tuple

from backend.config import DATA_DIRECTORY
from backend.services.dashboard_expression import load_default_push_date, normalize_show_date
from backend.services.project_data_paths import get_project_runtime_dir, resolve_project_runtime_path
from backend.services.project_registry import get_default_project_key

DATA_ROOT = Path(DATA_DIRECTORY).resolve()
DEFAULT_PROJECT_KEY = get_default_project_key()
CACHE_LOCK = Lock()
DEFAULT_CACHE_KEY = "__default__"
SPLIT_CACHE_DIRNAME = "dashboard_cache_v2"
LEGACY_CACHE_FILENAME = "dashboard_cache.json"
LEGACY_BACKUP_FILENAME = "dashboard_cache.legacy.json"
LAYOUT_VERSION = 2
EAST_8 = timezone(timedelta(hours=8))

SHARED_DATA_KEYS = (
    "口径别名",
    "项目字典",
    "单位字典",
)
DETAIL_SECTION_KEYS = {
    "0.5卡片详细信数据表（折叠）",
    "7.煤炭库存明细",
    "8.供热分中心单耗明细",
    "11.各单位运行设备数量明细表",
}
TREND_SECTION_KEYS = {
    "1.日均气温",
    "9.累计卡片",
    "10.标煤耗量与平均气温趋势图",
}
DATA_KEY_ORDER = (
    "push_date",
    "0.5卡片详细信数据表（折叠）",
    "1.日均气温",
    "2.边际利润",
    "3.集团汇总收入明细",
    "4.供暖单耗",
    "5.标煤耗量",
    "6.当日省市平台投诉量",
    "7.煤炭库存明细",
    "8.供热分中心单耗明细",
    "9.累计卡片",
    "10.标煤耗量与平均气温趋势图",
    "11.各单位运行设备数量明细表",
    "口径别名",
    "项目字典",
    "单位字典",
    "展示日期",
)


def _now_iso() -> str:
    return datetime.now(EAST_8).isoformat()


def _default_bundle(project_key: str) -> Dict[str, Any]:
    return {
        "project_key": project_key,
        "disabled": False,
        "items": {},
        "updated_at": None,
    }


def _default_index(project_key: str) -> Dict[str, Any]:
    return {
        "project_key": project_key,
        "layout_version": LAYOUT_VERSION,
        "disabled": False,
        "updated_at": None,
        "entries": {},
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


def _load_json_dict(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_json_dict(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _resolve_legacy_cache_file(project_key: str) -> Path:
    return resolve_project_runtime_path(project_key, LEGACY_CACHE_FILENAME)


def _resolve_legacy_backup_file(project_key: str) -> Path:
    project_path = get_project_runtime_dir(project_key) / LEGACY_BACKUP_FILENAME
    if project_path.exists():
        return project_path.resolve()
    fallback_path = (DATA_ROOT / LEGACY_BACKUP_FILENAME).resolve()
    return fallback_path


def _resolve_cache_root(project_key: str) -> Path:
    return (get_project_runtime_dir(project_key) / SPLIT_CACHE_DIRNAME).resolve()


def _resolve_index_file(project_key: str) -> Path:
    return _resolve_cache_root(project_key) / "index.json"


def _resolve_shared_file(project_key: str) -> Path:
    return _resolve_cache_root(project_key) / "shared.json"


def _entry_dirname(cache_key: str) -> str:
    return cache_key if cache_key != DEFAULT_CACHE_KEY else DEFAULT_CACHE_KEY


def _resolve_entry_dir(project_key: str, cache_key: str) -> Path:
    return _resolve_cache_root(project_key) / _entry_dirname(cache_key)


def _clear_split_cache_root(project_key: str) -> None:
    root = _resolve_cache_root(project_key)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def _extract_shared_data(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    shared: Dict[str, Any] = {}
    for key in SHARED_DATA_KEYS:
        if key in data:
            shared[key] = deepcopy(data[key])
    return shared


def _merge_shared_data(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in incoming.items():
        merged[key] = deepcopy(value)
    return merged


def _split_payload(
    payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    meta = {
        key: deepcopy(value)
        for key, value in payload.items()
        if key != "data"
    }
    data = payload.get("data")
    if not isinstance(data, dict):
        return meta, {}, {}, {}, {}

    shared = _extract_shared_data(data)
    summary: Dict[str, Any] = {}
    detail: Dict[str, Any] = {}
    trend: Dict[str, Any] = {}
    for key, value in data.items():
        if key in SHARED_DATA_KEYS:
            continue
        if key in DETAIL_SECTION_KEYS:
            detail[key] = deepcopy(value)
            continue
        if key in TREND_SECTION_KEYS:
            trend[key] = deepcopy(value)
            continue
        summary[key] = deepcopy(value)
    return meta, summary, detail, trend, shared


def _compose_data(
    summary: Dict[str, Any],
    detail: Dict[str, Any],
    trend: Dict[str, Any],
    shared: Dict[str, Any],
) -> Dict[str, Any]:
    combined: Dict[str, Any] = {}
    for part in (summary, detail, trend, shared):
        for key, value in part.items():
            combined[key] = deepcopy(value)

    ordered: Dict[str, Any] = {}
    for key in DATA_KEY_ORDER:
        if key in combined:
            ordered[key] = combined.pop(key)
    for key, value in combined.items():
        ordered[key] = value
    return ordered


def _write_entry_parts(
    project_key: str,
    cache_key: str,
    meta: Dict[str, Any],
    summary: Dict[str, Any],
    detail: Dict[str, Any],
    trend: Dict[str, Any],
) -> Dict[str, Any]:
    entry_dir = _resolve_entry_dir(project_key, cache_key)
    if entry_dir.exists():
        shutil.rmtree(entry_dir)
    entry_dir.mkdir(parents=True, exist_ok=True)

    _write_json_dict(entry_dir / "meta.json", meta)
    _write_json_dict(entry_dir / "summary.json", summary)
    _write_json_dict(entry_dir / "detail.json", detail)
    _write_json_dict(entry_dir / "trend.json", trend)

    return {
        "dir_name": entry_dir.name,
        "generated_at": meta.get("generated_at"),
        "show_date": meta.get("show_date"),
        "push_date": meta.get("push_date"),
        "parts": ["meta.json", "summary.json", "detail.json", "trend.json"],
    }


def _load_index(project_key: str) -> Dict[str, Any]:
    raw = _load_json_dict(_resolve_index_file(project_key))
    index = _default_index(project_key)
    if raw.get("project_key") not in (None, project_key):
        return index
    index["layout_version"] = raw.get("layout_version") or LAYOUT_VERSION
    index["disabled"] = bool(raw.get("disabled", False))
    index["updated_at"] = raw.get("updated_at")
    entries = raw.get("entries")
    if isinstance(entries, dict):
        for cache_key, entry in entries.items():
            if not isinstance(cache_key, str) or not isinstance(entry, dict):
                continue
            index["entries"][cache_key] = dict(entry)
    return index


def _write_index(project_key: str, index: Dict[str, Any]) -> None:
    payload = {
        "project_key": project_key,
        "layout_version": LAYOUT_VERSION,
        "disabled": bool(index.get("disabled", False)),
        "updated_at": index.get("updated_at"),
        "entries": deepcopy(index.get("entries", {})),
    }
    _write_json_dict(_resolve_index_file(project_key), payload)


def _build_split_cache(
    project_key: str,
    entries: Dict[str, Dict[str, Any]],
    disabled: bool = False,
    updated_at: str | None = None,
) -> Dict[str, Any]:
    _clear_split_cache_root(project_key)
    shared_payload: Dict[str, Any] = {}
    index = _default_index(project_key)
    index["disabled"] = bool(disabled)
    index["updated_at"] = updated_at or _now_iso()

    if not index["disabled"]:
        for cache_key, payload in entries.items():
            meta, summary, detail, trend, shared = _split_payload(payload)
            index["entries"][cache_key] = _write_entry_parts(
                project_key,
                cache_key,
                meta,
                summary,
                detail,
                trend,
            )
            shared_payload = _merge_shared_data(shared_payload, shared)

    _write_json_dict(_resolve_shared_file(project_key), shared_payload)
    _write_index(project_key, index)
    return index


def _migrate_legacy_cache_file(project_key: str) -> None:
    legacy_file = _resolve_legacy_cache_file(project_key)
    if not legacy_file.exists():
        return

    raw = _load_json_dict(legacy_file)
    bundle = _default_bundle(project_key)
    if raw.get("project_key") not in (None, project_key):
        return
    bundle["project_key"] = project_key
    bundle["disabled"] = bool(raw.get("disabled", False))
    bundle["updated_at"] = raw.get("updated_at")
    bundle["items"] = _sanitize_items(raw.get("items"))

    _build_split_cache(
        project_key,
        bundle["items"],
        disabled=bundle["disabled"],
        updated_at=bundle["updated_at"],
    )

    backup_file = _resolve_legacy_backup_file(project_key)
    if backup_file.exists():
        backup_file.unlink()
    legacy_file.replace(backup_file)


def _adopt_fallback_split_cache(project_key: str) -> None:
    project_root = _resolve_cache_root(project_key)
    fallback_root = (DATA_ROOT / SPLIT_CACHE_DIRNAME).resolve()
    if project_root.exists() or not fallback_root.exists():
        return
    project_root.parent.mkdir(parents=True, exist_ok=True)
    fallback_root.replace(project_root)

    fallback_legacy = (DATA_ROOT / LEGACY_BACKUP_FILENAME).resolve()
    project_legacy = (get_project_runtime_dir(project_key) / LEGACY_BACKUP_FILENAME).resolve()
    if fallback_legacy.exists() and not project_legacy.exists():
        project_legacy.parent.mkdir(parents=True, exist_ok=True)
        fallback_legacy.replace(project_legacy)


def _ensure_split_cache_ready(project_key: str) -> None:
    _adopt_fallback_split_cache(project_key)
    index_file = _resolve_index_file(project_key)
    if index_file.exists():
        return
    _migrate_legacy_cache_file(project_key)
    if not index_file.exists():
        _build_split_cache(project_key, {})


def _load_bundle(project_key: str) -> Dict[str, Any]:
    _ensure_split_cache_ready(project_key)
    index = _load_index(project_key)
    bundle = _default_bundle(project_key)
    bundle["disabled"] = index["disabled"]
    bundle["updated_at"] = index["updated_at"]
    bundle["items"] = {cache_key: {} for cache_key in index["entries"].keys()}
    return bundle


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
        _ensure_split_cache_ready(project_key)
        index = _load_index(project_key)
        status = {
            "disabled": index["disabled"],
            "available_dates": sorted(
                key for key in index["entries"].keys() if key != DEFAULT_CACHE_KEY
            ),
            "updated_at": index["updated_at"],
        }
        if index["disabled"]:
            return None, status

        entry = index["entries"].get(cache_key)
        if not isinstance(entry, dict):
            return None, status

        entry_dir = _resolve_cache_root(project_key) / str(entry.get("dir_name") or _entry_dirname(cache_key))
        meta = _load_json_dict(entry_dir / "meta.json")
        summary = _load_json_dict(entry_dir / "summary.json")
        detail = _load_json_dict(entry_dir / "detail.json")
        trend = _load_json_dict(entry_dir / "trend.json")
        shared = _load_json_dict(_resolve_shared_file(project_key))

    payload = deepcopy(meta)
    payload["data"] = _compose_data(summary, detail, trend, shared)
    return payload, status


def update_cache_entry(project_key: str, cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with CACHE_LOCK:
        _ensure_split_cache_ready(project_key)
        index = _load_index(project_key)
        shared_payload = _load_json_dict(_resolve_shared_file(project_key))
        meta, summary, detail, trend, shared = _split_payload(payload)
        shared_payload = _merge_shared_data(shared_payload, shared)
        _write_json_dict(_resolve_shared_file(project_key), shared_payload)
        index["entries"][cache_key] = _write_entry_parts(
            project_key,
            cache_key,
            meta,
            summary,
            detail,
            trend,
        )
        index["disabled"] = False
        index["updated_at"] = _now_iso()
        _write_index(project_key, index)
    return {
        "disabled": False,
        "available_dates": sorted(
            key for key in index["entries"].keys() if key != DEFAULT_CACHE_KEY
        ),
        "updated_at": index["updated_at"],
    }


def replace_cache(project_key: str, entries: Dict[str, Dict[str, Any]], disabled: bool = False) -> Dict[str, Any]:
    sanitized_entries = {
        key: deepcopy(value)
        for key, value in entries.items()
        if isinstance(key, str) and isinstance(value, dict)
    }
    with CACHE_LOCK:
        _build_split_cache(project_key, sanitized_entries, disabled=disabled)
    return get_cache_status(project_key)


def disable_cache(project_key: str) -> Dict[str, Any]:
    return replace_cache(project_key, {}, disabled=True)


def default_publish_dates(window: int = 7, project_key: str = DEFAULT_PROJECT_KEY) -> List[str]:
    """
    返回 set_biz_date 及其前 window-1 日（共 window 个日期），按时间升序排列。
    """
    base_iso = load_default_push_date(project_key)
    base_date = date.fromisoformat(base_iso)
    offsets = list(range(window - 1, -1, -1))
    ordered = [(base_date - timedelta(days=offset)).isoformat() for offset in offsets]
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


__all__ = [
    "DEFAULT_CACHE_KEY",
    "default_publish_dates",
    "disable_cache",
    "get_cache_status",
    "get_cached_payload",
    "replace_cache",
    "resolve_cache_key",
    "summarize_cache",
    "update_cache_entry",
]

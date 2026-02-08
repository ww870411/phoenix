# -*- coding: utf-8 -*-
"""项目目录化迁移辅助服务。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.project_data_paths import resolve_project_list_path
from backend.services.project_registry import get_project_modularization_files as get_registry_files


def _normalize_file_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    normalized: List[str] = []
    seen: Set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        name = Path(item.strip()).name
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _extract_filename_from_data_source(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or "开发中" in raw:
        return None
    filename = Path(raw).name
    if not filename or not filename.lower().endswith(".json"):
        return None
    return filename


def _infer_project_config_files_from_pages(project_entry: Dict[str, Any]) -> List[str]:
    pages_raw = project_entry.get("pages")
    collected: List[str] = []
    seen: Set[str] = set()

    def _append_from_data_source(value: Any) -> None:
        filename = _extract_filename_from_data_source(value)
        if not filename or filename in seen:
            return
        seen.add(filename)
        collected.append(filename)

    if isinstance(pages_raw, dict):
        for _page_url, meta in pages_raw.items():
            if not isinstance(meta, dict):
                continue
            _append_from_data_source(meta.get("数据源"))
            _append_from_data_source(meta.get("data_source"))
    elif isinstance(pages_raw, list):
        for entry in pages_raw:
            if not isinstance(entry, dict):
                continue
            for _page_name, config_file in entry.items():
                _append_from_data_source(config_file)
    return collected


def load_project_entries() -> Dict[str, Dict[str, Any]]:
    path = resolve_project_list_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    entries: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            entries[key] = value
    return entries


def load_project_entry(project_key: str) -> Optional[Dict[str, Any]]:
    return load_project_entries().get(project_key)


def resolve_project_modularization_files(
    project_key: str,
    project_entry: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    fallback_config_files, fallback_runtime_files = get_registry_files(project_key)
    entry = project_entry or {}

    modularization = (
        entry.get("modularization")
        or entry.get("目录化迁移")
        or entry.get("project_modularization")
    )
    config_files: List[str] = []
    runtime_files: List[str] = []
    if isinstance(modularization, dict):
        config_files.extend(
            _normalize_file_list(
                modularization.get("config_files")
                or modularization.get("config")
                or modularization.get("配置文件")
            )
        )
        runtime_files.extend(
            _normalize_file_list(
                modularization.get("runtime_files")
                or modularization.get("runtime")
                or modularization.get("运行时文件")
            )
        )

    if not config_files:
        config_files.extend(_infer_project_config_files_from_pages(entry))

    if not config_files:
        config_files = list(fallback_config_files)
    if not runtime_files:
        runtime_files = list(fallback_runtime_files)
    return config_files, runtime_files

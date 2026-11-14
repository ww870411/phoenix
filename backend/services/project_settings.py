# -*- coding: utf-8 -*-
"""
项目综合业务配置中心 (Project Settings Store)。

将原本分散在 runtime/ 与 config/ 中的低频、人工配置项统一整合到：
DATA_DIRECTORY/projects/<project_key>/config/project_settings.json

管理范围：
- biz_date: 全局基准业务日期（原 runtime/date.json）
- season: 供暖期运行参数（原 runtime/season_config.json）
- weather_near: 近端实况气温导入 API 与定时设置（原 runtime/weather_import_config.json + weather_auto_import_config.json 配置部分）
- weather_ensemble: 35天集合气温预报 API 与定时设置（原 runtime/ensemble_weather_* 配置部分）
- kdocs_complaint: 金山文档 12345 底表接入配置（原 config/kdocs_complaint_config.json 配置部分）
- spot_electricity: 电力现货自动同步配置（原 config/spot_electricity_sync_config.json 配置部分）

而高频更新的执行状态、历史记录与业务流转数据继续独立保存在 runtime/*_state.json 或 status.json 中，
避免多进程/多线程并发更新运行时日志时污染或覆盖业务配置。
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.config import DATA_DIRECTORY
from backend.services.project_data_paths import get_project_config_dir, get_project_runtime_dir

DEFAULT_PROJECT_KEY = "daily_report_25_26"
SETTINGS_FILENAME = "project_settings.json"
SETTINGS_SCHEMA_VERSION = 1

_SETTINGS_LOCK = threading.RLock()


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """原子替换 JSON 配置文件，确保 UTF-8 无 BOM 且避免读到半截文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = handle.name
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def read_json_dict(path: Path) -> Dict[str, Any]:
    """安全读取 JSON 字典，文件不存在时返回空字典；解析异常原样上抛。"""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"配置文件顶层必须为 JSON 对象: {path}")
    return raw


def get_project_settings_path(project_key: str = DEFAULT_PROJECT_KEY) -> Path:
    """返回项目综合配置文件路径：DATA_DIRECTORY/projects/<project_key>/config/project_settings.json。"""
    return (get_project_config_dir(project_key) / SETTINGS_FILENAME).resolve()


def _base_document() -> Dict[str, Any]:
    return {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def _read_settings_document_locked(settings_path: Path) -> Dict[str, Any]:
    if not settings_path.exists():
        return _base_document()
    raw = read_json_dict(settings_path)
    doc = _base_document()
    doc.update(raw)
    return doc


def get_settings_section(
    section: str,
    *,
    project_key: str = DEFAULT_PROJECT_KEY,
    defaults: Optional[Dict[str, Any]] = None,
    legacy_loader: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
    persist_if_migrated: bool = False,
) -> Dict[str, Any]:
    """
    读取综合配置中的指定节点。
    - 若目标节点已存在，直接合并 defaults 后返回；
    - 若目标节点尚未写入且提供了 legacy_loader，则尝试从旧配置文件读取；
      当 persist_if_migrated=True 且旧配置非空时，自动汇入 project_settings.json。
    """
    settings_path = get_project_settings_path(project_key)
    result: Dict[str, Any] = copy.deepcopy(defaults) if defaults else {}

    with _SETTINGS_LOCK:
        doc = _read_settings_document_locked(settings_path)
        existing = doc.get(section)
        if isinstance(existing, dict):
            result.update(copy.deepcopy(existing))
            return result

        if legacy_loader is not None:
            legacy_data = legacy_loader()
            if isinstance(legacy_data, dict) and legacy_data:
                result.update(copy.deepcopy(legacy_data))
                if persist_if_migrated:
                    doc[section] = copy.deepcopy(result)
                    doc["updated_at"] = datetime.now().astimezone().isoformat()
                    atomic_write_json(settings_path, doc)
                return result

    return result


def has_settings_section(section: str, *, project_key: str = DEFAULT_PROJECT_KEY) -> bool:
    """判断综合配置中是否已显式落盘指定配置节点。"""
    settings_path = get_project_settings_path(project_key)
    with _SETTINGS_LOCK:
        if not settings_path.exists():
            return False
        doc = _read_settings_document_locked(settings_path)
        return isinstance(doc.get(section), dict)


def update_settings_section(
    section: str,
    updates: Dict[str, Any],
    *,
    project_key: str = DEFAULT_PROJECT_KEY,
    defaults: Optional[Dict[str, Any]] = None,
    legacy_loader: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
    replace: bool = False,
) -> Dict[str, Any]:
    """
    线程安全且原子地更新综合配置中的指定节点：
    先在锁内重新读取完整 project_settings.json，仅更新目标 section，避免覆盖其它模块配置。
    """
    settings_path = get_project_settings_path(project_key)
    with _SETTINGS_LOCK:
        doc = _read_settings_document_locked(settings_path)
        current_section: Dict[str, Any] = copy.deepcopy(defaults) if defaults else {}

        existing = doc.get(section)
        if not replace:
            if isinstance(existing, dict):
                current_section.update(copy.deepcopy(existing))
            elif legacy_loader is not None:
                legacy_data = legacy_loader()
                if isinstance(legacy_data, dict):
                    current_section.update(copy.deepcopy(legacy_data))

        current_section.update(copy.deepcopy(updates))
        doc["schema_version"] = SETTINGS_SCHEMA_VERSION
        doc[section] = current_section
        doc["updated_at"] = datetime.now().astimezone().isoformat()
        atomic_write_json(settings_path, doc)
        return copy.deepcopy(current_section)


def get_runtime_state_path(filename: str, project_key: str = DEFAULT_PROJECT_KEY) -> Path:
    """返回项目 runtime/ 下的独立运行态文件路径。"""
    return (get_project_runtime_dir(project_key) / filename).resolve()


def resolve_legacy_kdocs_config_candidates(project_key: str = DEFAULT_PROJECT_KEY) -> list[Path]:
    """列出金山文档旧配置文件可能存放的位置（兼容相对路径与 DATA_DIRECTORY 路径）。"""
    return [
        (get_project_config_dir(project_key) / "kdocs_complaint_config.json").resolve(),
        (Path("backend_data") / "projects" / project_key / "config" / "kdocs_complaint_config.json").resolve(),
        (DATA_DIRECTORY / "projects" / project_key / "config" / "kdocs_complaint_config.json").resolve(),
    ]


def _read_first_legacy_dict(legacy_candidates: list[Path]) -> Dict[str, Any]:
    for candidate in legacy_candidates:
        if candidate.exists():
            try:
                loaded = read_json_dict(candidate)
                if loaded:
                    return loaded
            except Exception:
                continue
    return {}


def load_section_with_runtime_state(
    section: str,
    state_filename: str,
    defaults: Dict[str, Any],
    config_keys: tuple[str, ...],
    state_keys: tuple[str, ...],
    *,
    project_key: str = DEFAULT_PROJECT_KEY,
    legacy_candidates: Optional[list[Path]] = None,
) -> Dict[str, Any]:
    """
    通用加载：从 project_settings.json 读取业务配置键，从 runtime/<state_filename> 读取运行态键，
    并在首次读取且目标未落盘时兼容回退旧文件（legacy_candidates）后合并返回完整字典。
    """
    legacy_data = _read_first_legacy_dict(legacy_candidates or [])
    config_defaults = {k: defaults[k] for k in config_keys if k in defaults}
    state_defaults = {k: defaults[k] for k in state_keys if k in defaults}

    def _legacy_cfg_loader() -> Optional[Dict[str, Any]]:
        extracted = {k: legacy_data[k] for k in config_keys if k in legacy_data}
        return extracted or None

    cfg_part = get_settings_section(
        section,
        project_key=project_key,
        defaults=config_defaults,
        legacy_loader=_legacy_cfg_loader,
    )

    state_path = get_runtime_state_path(state_filename, project_key)
    state_part = copy.deepcopy(state_defaults)
    raw_state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            raw_state = read_json_dict(state_path)
        except Exception:
            raw_state = {}
    elif legacy_data:
        raw_state = legacy_data
    for k in state_keys:
        if k in raw_state:
            state_part[k] = copy.deepcopy(raw_state[k])

    merged = copy.deepcopy(defaults)
    merged.update(cfg_part)
    merged.update(state_part)
    return merged


def save_section_with_runtime_state(
    section: str,
    state_filename: str,
    full_payload: Dict[str, Any],
    config_keys: tuple[str, ...],
    state_keys: tuple[str, ...],
    *,
    project_key: str = DEFAULT_PROJECT_KEY,
    save_config: bool = True,
    save_state: bool = True,
) -> None:
    """将业务配置键写入 project_settings.json，将运行态键原子写入 runtime/<state_filename>。"""
    if save_config:
        cfg_payload = {k: full_payload[k] for k in config_keys if k in full_payload}
        if cfg_payload:
            update_settings_section(section, cfg_payload, project_key=project_key)
    if save_state:
        state_payload = {k: full_payload.get(k) for k in state_keys}
        atomic_write_json(get_runtime_state_path(state_filename, project_key), state_payload)


def _archive_file(src: Path, archive_dir: Path) -> Optional[Path]:
    """将已完成迁移的旧配置文件安全归档到 _archive 目录（若目标已存在则带时间戳后缀）。"""
    if not src.exists():
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / src.name
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = archive_dir / f"{src.stem}.{stamp}{src.suffix}"
    src.replace(target)
    return target


def migrate_legacy_project_settings(
    project_key: str = DEFAULT_PROJECT_KEY,
    *,
    archive_legacy: bool = True,
) -> Dict[str, Any]:
    """
    幂等迁移：将散落在 runtime/ 与 config/ 的纯业务配置汇入 config/project_settings.json，
    将执行历史与运行状态拆入 runtime/*_state.json，并可选把旧文件归档至 DATA_DIRECTORY/_archive/。
    """
    config_dir = get_project_config_dir(project_key)
    runtime_dir = get_project_runtime_dir(project_key)
    archive_root = (DATA_DIRECTORY / "_archive" / project_key / "migrated_legacy_configs").resolve()

    migrated_sections: list[str] = []
    migrated_states: list[str] = []
    archived_files: list[str] = []

    with _SETTINGS_LOCK:
        # 1. biz_date (date.json)
        date_candidates = [
            runtime_dir / "date.json",
            (DATA_DIRECTORY / "shared" / "date.json").resolve(),
            (DATA_DIRECTORY / "date.json").resolve(),
        ]
        if not has_settings_section("biz_date", project_key=project_key):
            legacy_date = _read_first_legacy_dict(date_candidates)
            if legacy_date.get("set_biz_date"):
                update_settings_section(
                    "biz_date",
                    {"set_biz_date": str(legacy_date["set_biz_date"]).strip()},
                    project_key=project_key,
                )
                migrated_sections.append("biz_date")
        if archive_legacy and has_settings_section("biz_date", project_key=project_key):
            moved = _archive_file(runtime_dir / "date.json", archive_root / "runtime")
            if moved:
                archived_files.append(str(moved))

        # 2. season (season_config.json)
        season_path = runtime_dir / "season_config.json"
        if not has_settings_section("season", project_key=project_key) and season_path.exists():
            try:
                season_raw = read_json_dict(season_path)
                if season_raw:
                    update_settings_section("season", season_raw, project_key=project_key)
                    migrated_sections.append("season")
            except Exception:
                pass
        if archive_legacy and has_settings_section("season", project_key=project_key):
            moved = _archive_file(season_path, archive_root / "runtime")
            if moved:
                archived_files.append(str(moved))

        # 3. weather_near + weather_ensemble
        weather_specs = [
            (
                "weather_near",
                runtime_dir / "weather_import_config.json",
                runtime_dir / "weather_auto_import_config.json",
                runtime_dir / "weather_auto_import_state.json",
            ),
            (
                "weather_ensemble",
                runtime_dir / "ensemble_weather_import_config.json",
                runtime_dir / "ensemble_weather_auto_import_config.json",
                runtime_dir / "ensemble_weather_auto_import_state.json",
            ),
        ]
        state_only_keys = (
            "last_attempt_time",
            "last_attempt_status",
            "last_attempt_trigger",
            "last_attempt_message",
            "last_success_time",
            "last_success_trigger",
            "last_success_message",
            "last_success_summary",
            "last_failure_time",
            "last_failure_trigger",
            "last_failure_message",
            "executed_slots_date",
            "executed_slots_today",
            "history",
        )
        for section, url_file, auto_file, state_file in weather_specs:
            url_data: Dict[str, Any] = {}
            auto_data: Dict[str, Any] = {}
            if url_file.exists():
                try:
                    url_data = read_json_dict(url_file)
                except Exception:
                    url_data = {}
            if auto_file.exists():
                try:
                    auto_data = read_json_dict(auto_file)
                except Exception:
                    auto_data = {}

            if not has_settings_section(section, project_key=project_key):
                cfg_payload: Dict[str, Any] = {}
                if isinstance(url_data.get("api_url"), str) and url_data["api_url"].strip():
                    cfg_payload["api_url"] = url_data["api_url"].strip()
                if "enabled" in auto_data:
                    cfg_payload["enabled"] = bool(auto_data["enabled"])
                if isinstance(auto_data.get("schedule_times"), list):
                    cfg_payload["schedule_times"] = list(auto_data["schedule_times"])
                if cfg_payload:
                    update_settings_section(section, cfg_payload, project_key=project_key)
                    migrated_sections.append(section)

            if not state_file.exists() and auto_data:
                state_payload = {k: auto_data.get(k) for k in state_only_keys if k in auto_data}
                if state_payload:
                    atomic_write_json(state_file, state_payload)
                    migrated_states.append(state_file.name)

            if archive_legacy:
                for src in (url_file, auto_file):
                    if src.exists():
                        moved = _archive_file(src, archive_root / "runtime")
                        if moved:
                            archived_files.append(str(moved))

        # 4. kdocs_complaint (kdocs_complaint_config.json)
        kdocs_cfg_keys = ("share_link", "share_id", "wps_sid", "description", "auto_sync_enabled")
        kdocs_state_keys = ("last_sync_time", "last_test_status", "last_test_time", "last_test_message")
        kdocs_candidates = resolve_legacy_kdocs_config_candidates(project_key)
        kdocs_legacy = _read_first_legacy_dict(kdocs_candidates)
        kdocs_state_file = runtime_dir / "kdocs_complaint_state.json"
        if not has_settings_section("kdocs_complaint", project_key=project_key) and kdocs_legacy:
            kdocs_cfg = {k: kdocs_legacy[k] for k in kdocs_cfg_keys if k in kdocs_legacy}
            if kdocs_cfg:
                update_settings_section("kdocs_complaint", kdocs_cfg, project_key=project_key)
                migrated_sections.append("kdocs_complaint")
        if not kdocs_state_file.exists() and kdocs_legacy:
            kdocs_state = {k: kdocs_legacy.get(k, "") for k in kdocs_state_keys}
            atomic_write_json(kdocs_state_file, kdocs_state)
            migrated_states.append(kdocs_state_file.name)
        if archive_legacy and has_settings_section("kdocs_complaint", project_key=project_key):
            for cand in kdocs_candidates:
                if cand.exists():
                    moved = _archive_file(cand, archive_root / "config")
                    if moved:
                        archived_files.append(str(moved))

        # 5. spot_electricity (spot_electricity_sync_config.json)
        spot_cfg_keys = ("enabled", "cron_time", "retry_interval_minutes", "max_retries_per_day", "target_date_rule")
        spot_state_keys = ("last_sync_date", "last_run_time", "last_run_status", "last_run_message", "next_run_time")
        spot_legacy_file = config_dir / "spot_electricity_sync_config.json"
        spot_state_file = runtime_dir / "spot_electricity_sync_state.json"
        spot_legacy: Dict[str, Any] = {}
        if spot_legacy_file.exists():
            try:
                spot_legacy = read_json_dict(spot_legacy_file)
            except Exception:
                spot_legacy = {}
        if not has_settings_section("spot_electricity", project_key=project_key) and spot_legacy:
            spot_cfg = {k: spot_legacy[k] for k in spot_cfg_keys if k in spot_legacy}
            if spot_cfg:
                update_settings_section("spot_electricity", spot_cfg, project_key=project_key)
                migrated_sections.append("spot_electricity")
        if not spot_state_file.exists() and spot_legacy:
            spot_state = {k: spot_legacy.get(k) for k in spot_state_keys}
            atomic_write_json(spot_state_file, spot_state)
            migrated_states.append(spot_state_file.name)
        if archive_legacy and has_settings_section("spot_electricity", project_key=project_key):
            if spot_legacy_file.exists():
                moved = _archive_file(spot_legacy_file, archive_root / "config")
                if moved:
                    archived_files.append(str(moved))

    return {
        "settings_path": str(get_project_settings_path(project_key)),
        "migrated_sections": migrated_sections,
        "migrated_states": migrated_states,
        "archived_files": archived_files,
    }


__all__ = [
    "DEFAULT_PROJECT_KEY",
    "SETTINGS_FILENAME",
    "SETTINGS_SCHEMA_VERSION",
    "atomic_write_json",
    "get_project_settings_path",
    "get_runtime_state_path",
    "get_settings_section",
    "has_settings_section",
    "load_section_with_runtime_state",
    "migrate_legacy_project_settings",
    "read_json_dict",
    "resolve_legacy_kdocs_config_candidates",
    "save_section_with_runtime_state",
    "update_settings_section",
]

# -*- coding: utf-8 -*-
"""
项目数据路径解析工具。

目标：
- 优先支持新目录：DATA_DIRECTORY/projects/<project_key>/{config|runtime}/...
- 向后兼容旧平铺目录：DATA_DIRECTORY/<filename>
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Iterable

from backend.config import DATA_DIRECTORY


def get_project_root(project_key: str) -> Path:
    """返回项目根目录：DATA_DIRECTORY/projects/<project_key>。"""
    return (DATA_DIRECTORY / "projects" / project_key).resolve()


def get_project_config_dir(project_key: str) -> Path:
    """返回项目配置目录。"""
    return (get_project_root(project_key) / "config").resolve()


def get_project_runtime_dir(project_key: str) -> Path:
    """返回项目运行时目录。"""
    return (get_project_root(project_key) / "runtime").resolve()


def resolve_project_config_path(project_key: str, filename: str) -> Path:
    """
    解析项目配置文件路径（读写兼容）：
    1) 若新路径存在，优先新路径；
    2) 否则回退旧平铺路径。
    """
    project_path = get_project_config_dir(project_key) / filename
    if project_path.exists():
        return project_path
    return (DATA_DIRECTORY / filename).resolve()


def resolve_project_runtime_path(project_key: str, filename: str) -> Path:
    """
    解析项目运行时文件路径（读写兼容）：
    1) 若新路径存在，优先新路径；
    2) 否则回退旧平铺路径。
    """
    project_path = get_project_runtime_dir(project_key) / filename
    if project_path.exists():
        return project_path
    return (DATA_DIRECTORY / filename).resolve()


def resolve_project_list_path() -> Path:
    """
    解析项目列表文件：
    1) DATA_DIRECTORY/shared/项目列表.json
    2) DATA_DIRECTORY/项目列表.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "项目列表.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "项目列表.json").resolve()


def resolve_accounts_path() -> Path:
    """
    解析账户信息文件：
    1) DATA_DIRECTORY/shared/auth/账户信息.json
    2) DATA_DIRECTORY/账户信息.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "auth" / "账户信息.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "账户信息.json").resolve()


def resolve_permissions_path() -> Path:
    """
    解析权限文件：
    1) DATA_DIRECTORY/shared/auth/permissions.json
    2) DATA_DIRECTORY/auth/permissions.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "auth" / "permissions.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "auth" / "permissions.json").resolve()


def resolve_global_date_path() -> Path:
    """
    解析全局日期文件（认证等全局逻辑使用）：
    1) DATA_DIRECTORY/shared/date.json
    2) DATA_DIRECTORY/date.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "date.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "date.json").resolve()


def resolve_workflow_status_path() -> Path:
    """
    解析审批状态文件（全局）：
    1) DATA_DIRECTORY/shared/status.json
    2) DATA_DIRECTORY/status.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "status.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "status.json").resolve()


def resolve_ai_usage_stats_path() -> Path:
    """
    解析 AI 使用量统计文件（全局）：
    1) DATA_DIRECTORY/shared/ai_usage_stats.json
    2) DATA_DIRECTORY/ai_usage_stats.json（兼容旧路径）
    """
    shared_path = (DATA_DIRECTORY / "shared" / "ai_usage_stats.json").resolve()
    if shared_path.exists():
        return shared_path
    return (DATA_DIRECTORY / "ai_usage_stats.json").resolve()


def ensure_project_dirs(project_key: str) -> Dict[str, str]:
    """
    创建项目目录骨架（若不存在则创建）。
    """
    project_root = get_project_root(project_key)
    config_dir = get_project_config_dir(project_key)
    runtime_dir = get_project_runtime_dir(project_key)
    config_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return {
        "project_root": str(project_root),
        "config_dir": str(config_dir),
        "runtime_dir": str(runtime_dir),
    }


def bootstrap_project_files(
    project_key: str,
    config_files: Iterable[str],
    runtime_files: Iterable[str],
) -> Dict[str, object]:
    """
    初始化项目目录并尝试复制旧平铺文件到新项目目录（仅在目标不存在时复制）。
    """
    dirs = ensure_project_dirs(project_key)
    copied_config: list[str] = []
    copied_runtime: list[str] = []
    skipped_config: list[str] = []
    skipped_runtime: list[str] = []

    for filename in config_files:
        target = get_project_config_dir(project_key) / filename
        legacy = (DATA_DIRECTORY / filename).resolve()
        if target.exists():
            skipped_config.append(filename)
            continue
        if legacy.exists():
            shutil.copy2(legacy, target)
            copied_config.append(filename)
        else:
            skipped_config.append(filename)

    for filename in runtime_files:
        target = get_project_runtime_dir(project_key) / filename
        legacy = (DATA_DIRECTORY / filename).resolve()
        if target.exists():
            skipped_runtime.append(filename)
            continue
        if legacy.exists():
            shutil.copy2(legacy, target)
            copied_runtime.append(filename)
        else:
            skipped_runtime.append(filename)

    return {
        "dirs": dirs,
        "copied_config": copied_config,
        "copied_runtime": copied_runtime,
        "skipped_config": skipped_config,
        "skipped_runtime": skipped_runtime,
    }


def get_project_file_status(
    project_key: str,
    config_files: Iterable[str],
    runtime_files: Iterable[str],
) -> Dict[str, object]:
    """
    返回项目目录与旧平铺目录的文件存在状态，用于迁移核对。
    """
    config_status: Dict[str, Dict[str, bool | str]] = {}
    runtime_status: Dict[str, Dict[str, bool | str]] = {}

    for filename in config_files:
        project_path = (get_project_config_dir(project_key) / filename).resolve()
        legacy_path = (DATA_DIRECTORY / filename).resolve()
        config_status[filename] = {
            "project_exists": project_path.exists(),
            "legacy_exists": legacy_path.exists(),
            "project_path": str(project_path),
            "legacy_path": str(legacy_path),
        }

    for filename in runtime_files:
        project_path = (get_project_runtime_dir(project_key) / filename).resolve()
        legacy_path = (DATA_DIRECTORY / filename).resolve()
        runtime_status[filename] = {
            "project_exists": project_path.exists(),
            "legacy_exists": legacy_path.exists(),
            "project_path": str(project_path),
            "legacy_path": str(legacy_path),
        }

    return {
        "project_key": project_key,
        "dirs": {
            "project_root": str(get_project_root(project_key)),
            "config_dir": str(get_project_config_dir(project_key)),
            "runtime_dir": str(get_project_runtime_dir(project_key)),
        },
        "config_files": config_status,
        "runtime_files": runtime_status,
    }
